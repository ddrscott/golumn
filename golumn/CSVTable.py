from __future__ import print_function
import csv
import time
import threading
import wx

SAMPLE_BYTES = 1024 * 64
SAMPLE_ROWS = 100


class CSVTable(wx.grid.GridTableBase):
    def __init__(self, src=None, headers=None):
        wx.grid.GridTableBase.__init__(self)

        self.headers = headers
        self.src_file = open(src, 'r')
        self.dialect = 'excel'
        self.data = list()
        self.csv_reader = self.build_csvreader(self.src_file)
        # Leave blank until this is finished loading
        self.original = None

        for i in range(0, SAMPLE_ROWS):
            row = next(self.csv_reader)
            if row:
                self.data.append(row)
            else:
                break

        if headers is None:
            self.first_line_header = True
            self.headers = self.data.pop(0)
        else:
            self.first_line_header = False
            self.headers = headers

        wx.CallLater(1, lambda: threading.Thread(target=self.load_data_bg).start())

    def load_data_bg(self):
        start = time.time()
        tick = time.time()
        added = 0
        for row in self.csv_reader:
            added += 1
            self.data.append(row)
            if (time.time() - tick) > 0.5:
                tick = time.time()
                wx.CallAfter(self.notify_grid_added, added)
                added = 0
        print('total time: ', time.time() - start)
        wx.CallAfter(self.notify_grid_added, added)
        

    def notify_grid_added(self, added):
        grid = self.GetView()
        grid.SetRowLabelSize(len(str(len(self.data))) * 8 + 8)
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, added))
        grid.EndBatch()
        grid.AdjustScrollbars()

    def build_csvreader(self, src_file):
        # reader = csv.reader(iter(m.readline, ""))
        sample = src_file.read(SAMPLE_BYTES)
        src_file.seek(0)
        try:
            # detect file type
            self.dialect = csv.Sniffer().sniff(sample)
        except Exception as err:
            wx.MessageBox("Error: {0}\n\nSetting to comma and double quote.".format(err), caption='Could not CSV dialect')

        return csv.reader(src_file, self.dialect)

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.headers[col]

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.headers)

    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return None

    def SetValue(self, row, col, value):
        self.data[row][col] = value

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
