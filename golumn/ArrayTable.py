from copy import copy
import wx
from operator import itemgetter

SAMPLE_SIZE = 10


class ArrayTable(wx.grid.GridTableBase):
    def __init__(self, data, headers=None):
        wx.grid.GridTableBase.__init__(self)
        if headers is None:
            self.headers = data.pop(0)
        else:
            self.headers = headers
        self.data = data
        self.original = self.data
        if len(self.data) > SAMPLE_SIZE:
            self.fakeLimit = SAMPLE_SIZE
            wx.CallLater(1, self.UnsetFakeLimit)
        else:
            self.fakeLimit = None

    def UnsetFakeLimit(self):
        self.fakeLimit = None
        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data) - SAMPLE_SIZE)
        self.GetView().ProcessTableMessage(msg)

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.headers[col]

    def GetNumberRows(self):
        if self.fakeLimit:
            return self.fakeLimit
        else:
            return len(self.data)

    def GetNumberCols(self):
        return len(self.headers)

    def IsEmptyCell(self, row, col):
        try:
            return not self.data[row][col]
        except IndexError:
            return True

    def GetValue(self, row, col):
        try:
            return self.data[row][col]
        except IndexError:
            return False

    def SetValue(self, row, col, value):
        self.data[row][col] = value

    def SortColumn(self, col, reverse=False):
        self.data = sorted(self.data, key=itemgetter(col), reverse=reverse)
        self.GetView().ForceRefresh()

    def remove_filter(self):
        grid = self.GetView()
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, len(self.data)))
        self.data = copy(self.original)
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data)))
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        grid.EndBatch()
        self.refresh_data()

    def filter_by(self, col, value):
        grid = self.GetView()
        grid.BeginBatch()
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, len(self.data)))
        self.data = [row for row in self.data if row[col] == value]
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data)))
        grid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES))
        grid.EndBatch()
        self.refresh_data()

    def refresh_data(self):
        grid = self.GetView()
        grid.AdjustScrollbars()
        grid.ForceRefresh()

