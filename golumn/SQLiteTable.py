from __future__ import print_function
from functools import lru_cache
import sqlite3
import time
import threading
import wx
from hashlib import md5
from pandas import read_csv

# number of CSV rows to process at a time
CSV_CHUNK_SIZE = 10000

# must be smaller than Panda Chunk Size
QUERY_PAGE_SIZE = 1000

# initial rows to display for auto sizing
INIT_ROW_AUTO_SIZE = 100

# status update interval
STATUS_UPDATE_INTERVAL_SEC = 0.314159


class SQLiteTable(wx.grid.GridTableBase):
    def __init__(self, src=None, dst_db='tmp/golumn.db', dst_table=None):
        wx.grid.GridTableBase.__init__(self)

        self.dst_db = dst_db
        self.conn = sqlite3.connect(dst_db)
        self.table = dst_table or ('_' + md5(src.encode('utf-8')).hexdigest())
        self.frames = read_csv(src, chunksize=CSV_CHUNK_SIZE)
        self.start_time = time.time()

        # Load first frame immediately into DB. Replace table if needed.
        self.first_frame = next(self.frames)
        self.first_frame.to_sql(self.table, self.conn, if_exists='replace', index=False)
        self.total_rows = len(self.first_frame)
        self.handle_fake_row_count()

        # for filtering
        self.where = list()
        self.where_fuzzy = None
        self.order_by = None

    def handle_fake_row_count(self):
        self.fake_row_count = None
        if len(self.first_frame) > INIT_ROW_AUTO_SIZE:
            self.fake_row_count = INIT_ROW_AUTO_SIZE

    def unset_fake_row_count(self):
        self.fake_row_count = None
        added = len(self.first_frame) - INIT_ROW_AUTO_SIZE
        wx.CallAfter(self.notify_grid_added, added)
        # background load the remaining data
        wx.CallAfter(lambda: threading.Thread(target=self.load_data_bg).start())

    def load_data_bg(self):
        tick = time.time()
        bg_conn = sqlite3.connect(self.dst_db)
        added = 0
        for frame in self.frames:
            frame.to_sql(self.table, bg_conn, if_exists='append', index=False)
            added += len(frame)
            self.total_rows += len(frame)
            if (time.time() - tick) > STATUS_UPDATE_INTERVAL_SEC:
                tick = time.time()
                wx.CallAfter(self.notify_grid_added, added)
                added = 0
        # final update
        wx.CallAfter(self.notify_grid_added, added)
        bg_conn.close()

    def update_row_status(self):
        self.set_status_text('time: {0:,.1f} s, rows: {1:,}'.format(time.time() - self.start_time, self.total_rows))

    def frame(self):
        return self.GetView().GetParent()

    def set_status_text(self, text):
        self.frame().set_status_text(text)

    def notify_grid_added(self, added):
        grid = self.GetView()
        self.update_row_status()
        grid.SetRowLabelSize(len(str(self.total_rows)) * 8 + 8)
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, added))
        grid.EndBatch()
        grid.AdjustScrollbars()

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.first_frame.columns[col]

    def GetNumberRows(self):
        if self.fake_row_count:
            wx.CallAfter(self.unset_fake_row_count)
            return self.fake_row_count
        return self.total_rows

    def GetNumberCols(self):
        return len(self.first_frame.columns)

    def IsEmptyCell(self, row, col):
        return False

    @lru_cache(maxsize=10)
    def fetch_query(self, query):
        wx.LogDebug("fetch query: {0}".format(query.replace('%', "%%")))
        return [r for r in self.conn.execute(query)]

    def quote_sql(self, text):
        return text.replace("'", "\\'")

    def build_query(self, select='*', limit=None, offset=None):
        """
        FIXME: This is probably called too often. We should find a way to make
               it faster or call it less.
        """
        query = ['SELECT', select, 'FROM', self.table]

        # make a copy so we don't keep appending stuff due to fuzzy finder
        where = list(self.where)
        if self.where_fuzzy:
            re = self.where_fuzzy.get('regexp', None)
            like = self.where_fuzzy.get('like', None)
            if re:
                where.append(' OR '.join(["({0} REGEXP '{1}')".format(h, self.quote_sql(re)) for h in self.headers()]))
            elif like:
                where.append(' OR '.join(["({0} LIKE '{1}')".format(h, self.quote_sql(like)) for h in self.headers()]))

        if len(where) > 0:
            query.append('WHERE ({0})'.format(') AND ('.join(where)))

        self.order_by and query.append('ORDER BY {0}'.format(self.order_by))
        limit and query.append('LIMIT {0}'.format(limit))
        offset and query.append('OFFSET {0}'.format(offset))
        return ' '.join(query)

    def GetValue(self, row, col):
        # calculate page needed
        limit = QUERY_PAGE_SIZE
        page_offset = row % QUERY_PAGE_SIZE
        offset = row - page_offset
        try:
            page = self.fetch_query(self.build_query(limit=limit, offset=offset))
            return page[page_offset][col]
        except Exception as err:
            return "!!{0}".format(err)
        return None

    def SetValue(self, row, col, value):
        None
        # self.data[row][col] = value

    def SortColumn(self, col, reverse=False):
        self.order_by = self.headers()[col]
        if reverse:
            self.order_by = self.order_by + ' DESC'
        self.GetView().ForceRefresh()

    def remove_filter(self):
        self.where.clear()
        self.order_by = None
        self.apply_query()

    def headers(self):
        # import code; code.interact(local=dict(globals(), **locals()))
        return self.first_frame.columns

    def select_count(self):
        return self.fetch_query(self.build_query(select='COUNT(1)'))[0][0]

    def filter_by(self, col, value):
        if value:
            self.where.append("{0} = '{1}'".format(self.headers()[col], value))
        else:
            self.where.append("{0} IS NULL".format(self.headers()[col]))

        self.apply_query()

    def apply_query(self):
        grid = self.GetView()
        row = grid.GetGridCursorRow()
        col = grid.GetGridCursorCol()
        new_total = self.select_count()
        # wx.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        # grid.GetParent().set_status_text('Loading...')
        grid.SetGridCursor(row, col)
        wx.LogDebug('filtered count: {0:,}'.format(new_total))
        grid.BeginBatch()
        if new_total < self.total_rows:
            grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, new_total + 1, self.total_rows - new_total))
        elif new_total > self.total_rows:
            grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, self.total_rows))
            grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, new_total))
        else:
            None
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        self.total_rows = new_total
        grid.EndBatch()
        grid.AdjustScrollbars()
        # try to put cursor back where it was
        if row > self.total_rows:
            row = self.total_rows
        grid.SetGridCursor(row, col)

    def fuzzy_filter(self, **kw):
        self.where_fuzzy = kw
        self.apply_query()
