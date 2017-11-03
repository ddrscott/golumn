import csv
import re
import wx
import ArrayTable
import tempfile

DEFAULT_COPY_DIALECT = 'excel-tab'


class ArrayGrid(wx.grid.Grid):
    def __init__(self, parent, data):
        wx.grid.Grid.__init__(self)
        self.Create(parent)

        # assign data adapter
        table = ArrayTable.ArrayTable(data=data)
        self.SetTable(table, True)
        self.SetColLabelSize(20)
        self.SetRowLabelSize(20)
        self.SetMargins(-10, -10)   # remove some whitespace, but leave enough for scrollbar overlap
        self.AutoSizeColumns(False)
        self.DisableDragRowSize()

        parent.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)

    def real_selection(self):
        """
        wxGrid selection is too flexible, we really just need these
        coordinates. This handles all that mess and returns the endpoints ready
        to apply to a range.
        """
        top, left, bottom, right = [0, 0, 0, 0]

        if self.GetSelectionBlockTopLeft():
            # Bug! Prevents me from accessing GridCellCoords directly.
            # This gets the values as strings and maps the digits to an
            # array of ints.
            #     GridCellCoordsArray: [GridCellCoords(2, 0)]
            # https://groups.google.com/forum/#!topic/wxpython-dev/Isw1L5_i6po
            top, left = map(int, re.findall('\d+', str(self.GetSelectionBlockTopLeft())))
            bottom, right = map(lambda x: int(x)+1, re.findall('\d+', str(self.GetSelectionBlockBottomRight())))
        elif self.GetSelectedCols():
            top = 0
            bottom = self.GetNumberRows()
            left, right = self.GetSelectedCols()[0], self.GetSelectedCols()[-1]+1
        elif self.GetSelectedRows():
            top, bottom = self.GetSelectedRows()[0], self.GetSelectedRows()[-1]+1
            left = 0
            right = self.GetNumberCols()
        elif self.GetGridCursorCol():
            top, bottom = self.GetGridCursorRow(), self.GetGridCursorRow()+1
            left, right = self.GetGridCursorCol(), self.GetGridCursorCol()+1

        return [top, bottom, left, right]

    def on_copy(self, evt):
        with tempfile.TemporaryFile() as file:
            writer = csv.writer(file, dialect=DEFAULT_COPY_DIALECT)

            top, bottom, left, right = self.real_selection()

            for r in range(top, bottom):
                row = []
                for c in range(left, right):
                    row.append(self.GetCellValue(r, c))
                writer.writerow(row)

            file.seek(0)

            if wx.TheClipboard.Open():
                clipData = wx.TextDataObject()
                clipData.SetText(file.read())
                wx.TheClipboard.SetData(clipData)
                wx.TheClipboard.Close()
            else:
                dlg = wx.MessageDialog(self, 'Could not open the clipboard for copying.\nUnknown error :(', 'Clipboard Error', wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
