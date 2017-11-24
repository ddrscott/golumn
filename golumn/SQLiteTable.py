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


class SQLiteTable(wx.grid.GridTableBase):
    def __init__(self, src=None, dst_db='tmp/golumn.db', dst_table=None):
        wx.grid.GridTableBase.__init__(self)

        self.dst_db = dst_db
        self.conn = sqlite3.connect(dst_db)
        self.table = dst_table or ('_' + md5(src.encode('utf-8')).hexdigest())
        self.frames = read_csv(src, chunksize=CSV_CHUNK_SIZE)

        # Load first frame immediately into DB. Replace table if needed.
        self.first_frame = next(self.frames)
        self.first_frame.to_sql(self.table, self.conn, if_exists='replace', index=False)
        self.total_rows = len(self.first_frame)
        self.handle_fake_row_count()

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
        start = time.time()
        tick = time.time()
        bg_conn = sqlite3.connect(self.dst_db)
        added = 0
        for frame in self.frames:
            frame.to_sql(self.table, bg_conn, if_exists='append', index=False)
            added += len(frame)
            self.total_rows += len(frame)
            if (time.time() - tick) > 0.5:
                tick = time.time()
                wx.CallAfter(self.notify_grid_added, added)
                added = 0
        wx.LogDebug('total time: {0:,.2f}'.format(time.time() - start))
        if added > 0:
            wx.CallAfter(self.notify_grid_added, added)
        bg_conn.close()

    def notify_grid_added(self, added):
        grid = self.GetView()
        grid.SetRowLabelSize(len(str(self.total_rows)) * 8 + 8)
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, added))
        grid.EndBatch()
        grid.AdjustScrollbars()
        grid.GetParent().status_row_count(self.total_rows)

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
        wx.LogDebug("fetch query: {0}".format(query))
        return [r for r in self.conn.execute(query)]

    def GetValue(self, row, col):
        # calculate page needed
        limit = QUERY_PAGE_SIZE
        page_offset = row % QUERY_PAGE_SIZE
        offset = row - page_offset
        try:
            query = 'SELECT * FROM {0} LIMIT {1} OFFSET {2}'.format(self.table, limit, offset)
            page = self.fetch_query(query)
            return page[page_offset][col]
        except Exception as err:
            return "Exception: {0}".format(err)
        return None

    def SetValue(self, row, col, value):
        None
        # self.data[row][col] = value

    def SortColumn(self, col, reverse=False):
        return
        self.data = sorted(self.data, key=lambda r: len(r) > col and r[col], reverse=reverse)
        self.GetView().ForceRefresh()

    def remove_filter(self):
        return
        grid = self.GetView()
        col = grid.GetGridCursorCol()
        row = grid.GetGridCursorRow()

        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, len(self.data)))
        self.data = self.original
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data)))
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        grid.EndBatch()
        self.refresh_data(row, col)

    def filter_by(self, col, value):
        return
        grid = self.GetView()
        row = grid.GetGridCursorRow()
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, len(self.data)))
        self.data = [r for r in self.data if len(r) > col and r[col] == value]
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data)))
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        grid.EndBatch()
        self.refresh_data(row, col)

    def fuzzy_filter(self, regexp):
        return
        # always start by restoring the original
        if self.original != self.data:
            self.remove_filter()

        grid = self.GetView()
        row = grid.GetGridCursorRow()
        col = grid.GetGridCursorCol()
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, len(self.data)))
        self.data = [r for r in self.data for c in r if regexp.match(c)]
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data)))
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        grid.EndBatch()
        self.refresh_data(row, col)

    def refresh_data(self, row, col):
        # return
        """row, col -  where to try to put the cursor when we're done"""
        grid = self.GetView()
        # try to put the cursor in the same spot it was before
        if row > len(self.data):
            row = len(self.data) - 1
        grid.SetGridCursor(row, col)
        grid.reset_view()
