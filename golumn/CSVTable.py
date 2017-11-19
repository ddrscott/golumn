import csv
import tempfile
import threading
import wx
from pandas import read_csv

SAMPLE_SIZE = 100


def line_index(src):
    counts = list()
    offset = 0
    with open(src, "r") as f:
        for line in f:
            size = len(line)
            offset += size
            counts.append((size, offset))
    return counts


class CSVTable(wx.grid.GridTableBase):
    def __init__(self, src=None, headers=None):
        wx.grid.GridTableBase.__init__(self)

        self.src = src
        self.headers = headers
        self.data = self.sample_data()

        if headers is None:
            self.first_line_header = True
            self.headers = self.data.pop(0)
        else:
            self.first_line_header = False
            self.headers = headers

        self.line_index = None

        def build_line_index():
            print "build_line_count: started"
            self.line_index = line_index(self.src)
            if self.first_line_header:
                self.line_index.pop(0)
            print "build_line_count: finished. size: %i" % len(self.line_index)
            wx.CallAfter(self.on_line_index)

        t = threading.Thread(target=build_line_index)
        t.setDaemon(True)
        t.start()

    def sample_data(self):
        with tempfile.TemporaryFile() as tmp:
            lines = 0
            with open(self.src, "r") as src_file:
                for line in src_file:
                    lines += 1
                    tmp.write(line)
                    if lines >= SAMPLE_SIZE:
                        break
            tmp.seek(0)

            sniff = tmp.read()
            tmp.seek(0)
            sample = list()
            csvreader = None
            self.dialect = None
            try:
                # detect file type
                self.dialect = csv.Sniffer().sniff(sniff)
                csvreader = csv.reader(tmp, self.dialect)
            except Exception:
                wx.MessageBox('Setting to comman', caption='Could not delimiter')
                csvreader = csv.reader(tmp)

            # convert csv reader to rows
            for row in csvreader:
                sample.append(row)
        return sample

    def on_line_index(self):
        grid = self.GetView()
        col = grid.GetGridCursorCol()
        row = grid.GetGridCursorRow()
        grid.SetRowLabelSize(len(str(self.GetNumberRows())) * 8 + 8)
        grid.BeginBatch()
        grid.ProcessTableMessage(
                wx.grid.GridTableMessage(
                    self,
                    wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
                    len(self.line_index) - len(self.data)
                    )
                )
        grid.EndBatch()
        self.refresh_data(row, col)
        self.src_file = open(self.src, 'rb')

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.headers[col]

    def GetNumberRows(self):
        if self.line_index:
            return len(self.line_index)
        return len(self.data)

    def GetNumberCols(self):
        return len(self.headers)

    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return self.get_value_from_src(row, col)

    def get_value_from_src(self, row, col):
        line = None
        size, offset = self.line_index[row]
        self.src_file.seek(offset)
        line = self.src_file.read(size)
        line = line.rstrip()

        # try:
        #     return line.split(',')[col]
        # except IndexError:
        #     return None

        try:
            csvreader = None
            if self.dialect:
                csvreader = csv.reader([line], self.dialect)
            else:
                csvreader = csv.reader([line])

            row = csvreader.next()
            return row[col]
        except Exception:
            import sys, traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
            return None

        print row[col]
        return None
        # self.data.append(row)
        return row[col]

    def get_value_from_src_bak(self, row, col):
        line = None
        with open(self.src, 'r') as f:
            size, offset = self.line_index[row]
            f.seek(offset)
            line = f.read(size)
        line = line.rstrip()

        return line.split(',')[col]

        csvreader = None
        if self.dialect:
            csvreader = csv.reader([line], self.dialect)
        else:
            csvreader = csv.reader([line])

        row = csvreader.next()
        print row[col]
        return None
        # self.data.append(row)
        return row[col]


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
