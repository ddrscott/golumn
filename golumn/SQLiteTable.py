import csv
import io
import logging
import sqlite3
import time
import threading
import wx
from functools import lru_cache
from hashlib import md5

import golumn
from golumn.SQLiteImporter import SQLiteImporter
from golumn.Utils import unique_array, detect_encoding
import golumn.typer

SNIFF_BYTES = 65535

# number of CSV rows to process at a time
CSV_CHUNK_SIZE = 10000

# must be smaller than Panda Chunk Size
QUERY_PAGE_SIZE = 1000

# initial rows to display for auto sizing
INIT_ROW_AUTO_SIZE = 100

# status update interval
STATUS_UPDATE_INTERVAL_SEC = 0.314159

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SQLiteTable(wx.grid.GridTableBase):
    def __init__(self, src, dst_db='tmp/golumn.db', dst_table=None, dialect=None):
        wx.grid.GridTableBase.__init__(self)

        logger.info('destination db: {0}'.format(dst_db))

        self.dst_db = dst_db

        if 'file::memory' in dst_db:
            self.conn = sqlite3.connect(dst_db, uri=True)
        else:
            self.conn = sqlite3.connect(dst_db)

        self.table = dst_table or ('_' + md5(src.encode('utf-8')).hexdigest())
        if dialect is not None:
            self.csvreader = self.simple_csvreader(src, dialect)
        else:
            self.csvreader = self.sniff_csvreader(src)
        self.headers = unique_array(next(self.csvreader))
        self.start_time = time.time()

        # import first chunk before starting background load
        rows = self.read_chunk()
        self.column_types = golumn.typer.detect_columns(rows)

        self.importer = SQLiteImporter(self.headers, db=dst_db, table=self.table)
        self.importer.create_table(rows, self.column_types)
        self.importer.close()

        self.total_rows = len(rows)
        self.initial_rows = len(rows)
        self.handle_fake_row_count()

        # for filtering
        self.where = list()
        self.where_fuzzy = None
        self.order_by = None

        self.force_value = None
        """Force a specific value returned from GetValue. Useful for optimizations.
        There are many many methods which select all rows for no useful reason.
        Setting this value will make the retrieve of all the rows very fast.
        """

        # events
        wx.CallAfter(self.bind_events)

    def bind_events(self, evt=None):
        pass

    def clean_up(self):
        if self.conn:
            if  'file::memory' in self.dst_db:
                logger.debug('in memory db. nothing to clean up')
            else:
                logger.debug('clean up database')
                drop_stmt = 'DROP TABLE IF EXISTS {0}'.format(self.table)
                logger.debug('exec sql: {0}'.format(drop_stmt))
                self.conn.execute(drop_stmt)
                logger.debug('exec sql: VACUUM')
                self.conn.execute('VACUUM')
            self.conn.close()
            logger.debug('connection closed')
            self.conn = None

    def read_chunk(self):
        rows = list()
        try:
            for i in range(0, CSV_CHUNK_SIZE):
                row = next(self.csvreader)
                if row:
                    rows.append(row)
                else:
                    break
        except(StopIteration):
            pass
        return rows

    def simple_csvreader(self, src, dialect):
        encoding = detect_encoding(src)
        self.src_file = io.open(src, 'r', encoding=encoding, errors='ignore')
        self.dialect = dialect
        return csv.reader(self.src_file, self.dialect)

    def sniff_csvreader(self, src):
        encoding = detect_encoding(src)
        self.src_file = io.open(src, 'r', encoding=encoding, errors='ignore')
        sample = self.src_file.read(SNIFF_BYTES)
        self.src_file.seek(0)
        self.dialect = csv.excel
        try:
            # detect file type
            self.dialect = csv.Sniffer().sniff(sample, delimiters=''.join(golumn.DELIMITERS.keys()))
            logger.debug("[sniff_csvreader] delimiter: {0}, quotechar: {0}".format(repr(self.dialect.delimiter), repr(self.dialect.quotechar)))
        except Exception as err:
            self.dialect.delimiter = u','
            self.dialect.quotechar = u'"'
            logger.debug("Error: {0}\n\nSetting parser to use comma separator and double quotes.".format(err))
        return csv.reader(self.src_file, self.dialect)

    def handle_fake_row_count(self):
        self.fake_row_count = None
        if self.initial_rows > INIT_ROW_AUTO_SIZE:
            self.fake_row_count = INIT_ROW_AUTO_SIZE
        else:
            wx.CallAfter(self.update_row_status)

    def unset_fake_row_count(self):
        self.fake_row_count = None
        added = self.initial_rows - INIT_ROW_AUTO_SIZE
        wx.CallAfter(self.notify_grid_added, added)
        wx.BeginBusyCursor()
        # background load the remaining data
        wx.CallAfter(lambda: threading.Thread(target=self.load_data_bg).start())

    def load_data_bg(self):
        tick = time.time()
        added = 0
        rows = list()
        parent = self.GetView().GetParent()
        num_headers = len(self.headers)
        importer = SQLiteImporter(self.headers, db=self.dst_db, table=self.table)
        for row in self.csvreader:
            if parent.closing:
                logger.debug('frame is closing. load data halted.')
                break
            rows.append(row[:num_headers])
            added += 1
            self.total_rows += 1
            if len(rows) >= CSV_CHUNK_SIZE:
                importer.insert(rows)
                del rows[:]
            if (time.time() - tick) > STATUS_UPDATE_INTERVAL_SEC:
                tick = time.time()
                wx.CallAfter(self.notify_grid_added, added)
                added = 0
        if not parent.closing:
            # final update
            if len(rows) > 0:
                importer.insert(rows)
            if added > 0:
                wx.CallAfter(self.notify_grid_added, added)
        importer.close()
        wx.EndBusyCursor()

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
        return self.headers[col]

    def GetNumberRows(self):
        if self.fake_row_count:
            wx.CallAfter(self.unset_fake_row_count)
            return self.fake_row_count
        return self.total_rows

    def GetNumberCols(self):
        return len(self.headers)

    def IsEmptyCell(self, row, col):
        return False

    @lru_cache(maxsize=10)
    def fetch_query(self, query):
        logger.debug("fetch query: {0}".format(query.replace('%', "%%")))
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
                where.append(' OR '.join(["(`{0}` REGEXP '{1}')".format(h, self.quote_sql(re)) for h in self.headers]))
            elif like:
                where.append(' OR '.join(["(`{0}` LIKE '{1}')".format(h, self.quote_sql(like)) for h in self.headers]))

        if len(where) > 0:
            query.append('WHERE ({0})'.format(') AND ('.join(where)))

        self.order_by and query.append('ORDER BY {0}'.format(self.order_by))
        limit and query.append('LIMIT {0}'.format(limit))
        offset and query.append('OFFSET {0}'.format(offset))
        return ' '.join(query)

    def GetValue(self, row, col):
        if self.force_value is not None:
            return self.force_value

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
        self.order_by = '`' + self.headers[col] + '`'
        if reverse:
            self.order_by = self.order_by + ' DESC'
        self.GetView().ForceRefresh()

    def remove_filter(self):
        del self.where[:]
        self.order_by = None
        self.apply_query()

    def select_count(self):
        return self.fetch_query(self.build_query(select='COUNT(1)'))[0][0]

    def filter_by(self, col, value):
        if value:
            self.where.append("`{0}` = '{1}'".format(self.headers[col], value))
        else:
            self.where.append("`{0}` IS NULL".format(self.headers[col]))
        self.apply_query()

    def exclude_by(self, col, value):
        if value:
            self.where.append("`{0}` <> '{1}'".format(self.headers[col], value))
        else:
            self.where.append("`{0}` IS NOT NULL".format(self.headers[col]))
        self.apply_query()

    def apply_query(self):
        grid = self.GetView()
        row = grid.GetGridCursorRow()
        col = grid.GetGridCursorCol()
        start = time.time()
        new_total = self.select_count()

        self.set_status_text('time: {0:,.1f} s, rows: {1:,}'.format(time.time() - start, new_total))
        grid.BeginBatch()
        if new_total < self.total_rows:
            grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, new_total, self.total_rows - new_total))
        elif new_total > self.total_rows:
            grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, new_total - self.total_rows))
        else:
            None
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        self.total_rows = new_total
        grid.EndBatch()
        grid.AdjustScrollbars()
        grid.ForceRefresh()
        # try to put cursor back where it was
        if row >= self.total_rows:
            row = self.total_rows - 1

        if new_total > 0 and row and col:
            wx.CallAfter(lambda: grid.SetGridCursor(row, col))

    def fuzzy_filter(self, **kw):
        self.where_fuzzy = kw
        self.apply_query()
