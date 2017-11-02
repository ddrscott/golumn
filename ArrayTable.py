import wx


SAMPLE_SIZE = 10


class ArrayTable(wx.grid.GridTableBase):
    def __init__(self, data, headers=None):
        wx.grid.GridTableBase.__init__(self)
        if headers is None:
            self.headers = data.pop(0)
        else:
            self.headers = headers
        self.data = data
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
        return not self.data[row][col]

    def GetValue(self, row, col):
        return self.data[row][col]

    def SetValue(self, row, col, value):
        self.data[row][col] = value

