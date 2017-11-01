import os
import sys
import csv
import wx
import wx.grid

try:
    import agw.flatnotebook as FNB
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.flatnotebook as FNB


class ArrayTable(wx.grid.GridTableBase):
    def __init__(self, data):
        wx.grid.GridTableBase.__init__(self)
        self.data = data

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.data[0])

    def IsEmptyCell(self, row, col):
        return not self.data[row][col]

    # Get/Set values in the table.  The Python version of these
    # methods can handle any data-type, (as long as the Editor and
    # Renderer understands the type too,) not just strings as in the
    # C++ version.
    def GetValue(self, row, col):
        return self.data[row][col]

    def SetValue(self, row, col, value):
        self.data[row][col] = value


class ArrayGrid(wx.grid.Grid):
    def __init__(self, parent, data):
        wx.grid.Grid.__init__(self)

        self.Create(parent)
        # self.data = data
        table = ArrayTable(data=data)
        self.SetTable(table, True)
        self.AutoSizeColumns(setAsMin=False)


def main():
    # get data from stdin or a file name
    file_name = sys.argv[1]
    with open(file_name, 'rb') as csvfile:
        # detect file type
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        csvreader = csv.reader(csvfile, dialect)

        # convert csv reader to rows
        rows = []
        for row in csvreader:
            rows.append(row)

        app = wx.App()
        title = os.path.basename(file_name)
        frm = wx.Frame(None, title=title, size=(700, 500))
        ArrayGrid(frm, rows)

        frm.Show()
        app.MainLoop()

if __name__ == '__main__':
    main()
