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

        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_cell_right_click)

    def on_cell_right_click(self, evt=None):
        if not hasattr(self, "evt_sort_a"):
            self.evt_sort_a = wx.NewId()
            self.evt_sort_z = wx.NewId()
            self.evt_filter_selection = wx.NewId()
            self.evt_remove_filter = wx.NewId()
            self.Bind(wx.EVT_MENU, self.on_sort_a, id=self.evt_sort_a)
            self.Bind(wx.EVT_MENU, self.on_sort_z, id=self.evt_sort_z)
            self.Bind(wx.EVT_MENU, self.on_filter_selection, id=self.evt_filter_selection)
            self.Bind(wx.EVT_MENU, self.on_remove_filter, id=self.evt_remove_filter)

        self.SetGridCursor(evt.GetRow(), evt.GetCol())

        # make a menu
        menu = wx.Menu()
        # Show how to put an icon in the menu
        menu.Append(wx.MenuItem(menu, self.evt_sort_a, "Sort &A..Z"))
        menu.Append(wx.MenuItem(menu, self.evt_sort_z, "Sort &Z..A"))
        menu.AppendSeparator()
        menu.Append(wx.MenuItem(menu, self.evt_filter_selection, "Filter by &Selection"))
        menu.Append(wx.MenuItem(menu, self.evt_remove_filter, "&Remove Filter"))

        self.PopupMenu(menu)
        menu.Destroy()

    def on_sort_a(self, evt=None):
        # self.SetSortingColumn(self.GetGridCursorCol(), ascending=True)
        self.GetTable().SortColumn(self.GetGridCursorCol(), reverse=False)

    def on_sort_z(self, evt=None):
        # self.SetSortingColumn(self.GetGridCursorCol(), ascending=False)
        self.GetTable().SortColumn(self.GetGridCursorCol(), reverse=True)

    def on_filter_selection(self, evt=None):
        value = self.GetCellValue(self.GetGridCursorRow(), self.GetGridCursorCol())
        self.GetTable().filter_by(self.GetGridCursorCol(), value)

    def on_remove_filter(self, evt=None):
        self.GetTable().remove_filter()

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
