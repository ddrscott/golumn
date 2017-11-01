import os
import sys
import csv
import wx
import wx.grid
import wx.aui

try:
    import agw.flatnotebook as FNB
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.flatnotebook as FNB


class ArrayTable(wx.grid.GridTableBase):
    def __init__(self, data, headers=None):
        wx.grid.GridTableBase.__init__(self)
        if headers is None:
            self.headers = data.pop(0)
        else:
            self.headers = headers
        self.data = data

        if len(self.data) > 100:
            self.fakeLimit = 100
            wx.CallLater(1, self.UnsetFakeLimit)

    def UnsetFakeLimit(self):
        self.fakeLimit = None
        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, len(self.data) - 100)
        self.GetView().ProcessTableMessage(msg)

    # Called when the grid needs to display labels
    def GetColLabelValue(self, col):
        return self.headers[col]

    def GetNumberRows(self):
        if self.fakeLimit is not None:
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


class ArrayGrid(wx.grid.Grid):
    def __init__(self, parent, data):
        wx.grid.Grid.__init__(self)
        self.Create(parent)

        # assign data adapter
        table = ArrayTable(data=data)
        self.SetTable(table, True)
        self.SetColLabelSize(20)
        self.SetRowLabelSize(0)
        self.SetMargins(-20, -20)   # remove whitespace around whole grid
        self.AutoSizeColumns(False)


class GolumnApp(wx.App):

    def OnInit(self):
        self.SetAppName('Golumn')
        self.frm = wx.Frame(None, size=(640, 400))
        self.frm.Centre()
        self.frm.Show()
        return True

    def LoadData(self, title, rows):
        # Setup the grid BEFORE the frame
        self.grid = ArrayGrid(self.frm, rows)
        self.grid.Fit()

        # load as frame
        self.frm.SetTitle(title)
        # force scrollbars to redraw
        self.frm.PostSizeEvent()


def main():
    # verify no other instance is running
    checker = wx.SingleInstanceChecker("Golumn")
    if checker.IsAnotherRunning():
        print("TODO Another instance is running. Reuse it, please.")

    # get data from stdin or a file name
    file_name = sys.argv[1]
    title = os.path.basename(file_name)
    rows = []
    with open(file_name, 'rb') as csvfile:

        # detect file type
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        csvreader = csv.reader(csvfile, dialect)

        # convert csv reader to rows
        for row in csvreader:
            rows.append(row)

    app = GolumnApp(useBestVisual=True)
    app.LoadData(title, rows)
    app.MainLoop()


if __name__ == '__main__':
    main()
