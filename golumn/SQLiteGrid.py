from __future__ import division
from __future__ import absolute_import
import csv
import re
import wx
import tempfile

import golumn.App
from golumn.SQLiteTable import SQLiteTable
import golumn.events as events
import golumn.key_bindings as key_bindings
import golumn.key_bindings.vim as vim

DEFAULT_COPY_DIALECT = 'excel-tab'


class SQLiteGrid(wx.grid.Grid):
    def __init__(self, parent, src):
        self.src = src
        wx.grid.Grid.__init__(self)
        self.Create(parent)
        self.EnableEditing(False)

        self.default_font_size = 12
        self.font_size = self.default_font_size

        self.table = SQLiteTable(src=src, dst_db=golumn.App.database_path())
        self.SetTable(self.table, False)
        for i, ct in enumerate(self.table.column_types):
            if ct == 'numeric' or ct == 'integer':
                attr = wx.grid.GridCellAttr()
                attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
                self.SetColAttr(i, attr)
        self.SetColLabelSize(self.font_size + 8)
        self.SetRowLabelSize(self.font_size + 18)
        self.SetMargins(-10, -10)   # remove some whitespace, but leave enough for scrollbar overlap
        self.DisableDragRowSize()
        self.SetUseNativeColLabels()
        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        parent.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
        parent.Bind(wx.EVT_MENU, self.on_sort_a, id=wx.ID_SORT_ASCENDING)
        parent.Bind(wx.EVT_MENU, self.on_sort_z, id=wx.ID_SORT_DESCENDING)
        parent.Bind(wx.EVT_MENU, self.on_remove_filter, id=golumn.App.ID_REMOVE_FILTER)
        parent.Bind(wx.EVT_MENU, self.on_filter_selection, id=golumn.App.ID_FILTER_BY_SELECTION)
        parent.Bind(wx.EVT_MENU, self.on_zoom_in, id=wx.ID_ZOOM_IN)
        parent.Bind(wx.EVT_MENU, self.on_zoom_out, id=wx.ID_ZOOM_OUT)
        parent.Bind(wx.EVT_MENU, self.on_zoom_reset, id=wx.ID_ZOOM_100)

        # bind to aggregate selection
        self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.on_label_right_click)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_left_dbl_click)
        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_cell_right_click)
        self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.on_calc_aggregates)
        self.Bind(events.EVT_AGG_SUM, self.on_agg_sum)
        self.Bind(events.EVT_AGG_COUNT, self.on_agg_count)
        self.Bind(events.EVT_AGG_AVG, self.on_agg_avg)
        self.bind_motions()
        self.AutoSize()

    def on_agg_sum(self, evt=None):
        print('on_agg_sum')

    def on_agg_count(self, evt=None):
        print('on_agg_count')

    def on_agg_avg(self, evt=None):
        print('on_agg_avg')

    # TODO: make a pure SQL implementation
    def on_calc_aggregates(self, evt=None):
        """
        Iterate through entire selection to calculate the aggregate numbers.
        Then updates `agg_text` with the correct value.
        """
        top, bot, left, right, single = self.real_selection()
        parent = self.GetParent()
        count = 0
        sum = 0
        avg_count = 0
        for r in range(top, bot):
            for c in range(left, right):
                try:
                    v = self.GetCellValue(r, c)
                    ct = self.table.column_types[c]
                    if ct == 'numeric':
                        sum += float(v)
                        avg_count += 1
                    elif ct == 'integer':
                        sum += int(v)
                        avg_count += 1
                    if v and len(str(v)) > 0:
                        count += 1
                except (TypeError, ValueError):
                    pass
        agg_text = 'sum: {0:,} | count: {1:,} | avg: {2:,}'.format(sum, count, sum / (avg_count if avg_count > 0 else 1))
        # if parent.ch_aggregate.Selection == 0:
        #     parent.agg_text.SetValue("= {0:,}".format(sum))
        # elif parent.ch_aggregate.Selection == 1 and avg_count > 0:
        #     parent.agg_text.SetValue("= {0:,}".format(float(sum) / avg_count))
        # elif parent.ch_aggregate.Selection == 2:
        #     parent.agg_text.SetValue("= {0:,}".format(count))

        parent.set_aggregate_text(agg_text)

    def on_label_right_click(self, evt=None):
        evt.Skip()

    def on_label_left_dbl_click(self, evt=None):
        evt.Skip()

    def on_zoom_in(self, evt=None):
        self.font_size = self.font_size * 1.1
        self.reset_font()

    def on_zoom_out(self, evt=None):
        self.font_size = self.font_size / 1.1
        self.reset_font()

    def on_zoom_reset(self, evt=None):
        self.font_size = self.default_font_size
        self.reset_font()

    def reset_font(self):
        self.SetDefaultCellFont(wx.Font( wx.FontInfo(int(round(self.font_size)))))
        # FIXME: This is really slow on large datasets.
        #        We should remove non visible rows, AutoSize, then put them back.
        self.AutoSize()
        self.reset_view()

    def on_select_cell(self, evt=None):
        if hasattr(self, 'force_grid_cursor'):
            del self.force_grid_cursor
        else:
            self.force_grid_cursor = True
            wx.CallAfter(self.SetGridCursor, evt.GetRow(), evt.GetCol())

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
        menu.Append(wx.MenuItem(menu, self.evt_sort_a, "Sort &A..Z\tShift+Ctrl+A"))
        menu.Append(wx.MenuItem(menu, self.evt_sort_z, "Sort &Z..A\tShift+Ctrl+Z"))
        menu.AppendSeparator()
        menu.Append(wx.MenuItem(menu, self.evt_filter_selection, "Filter by &Selection\tShift+Ctrl+S"))
        menu.Append(wx.MenuItem(menu, self.evt_remove_filter, "&Remove Sort and Filter\tShift+Ctrl+R"))

        self.PopupMenu(menu)
        menu.Destroy()

    def on_sort_a(self, evt=None):
        self.SetSortingColumn(self.GetGridCursorCol(), ascending=True)
        self.GetTable().SortColumn(self.GetGridCursorCol(), reverse=False)

    def on_sort_z(self, evt=None):
        self.SetSortingColumn(self.GetGridCursorCol(), ascending=False)
        self.GetTable().SortColumn(self.GetGridCursorCol(), reverse=True)

    def on_filter_selection(self, evt=None):
        value = self.GetCellValue(self.GetGridCursorRow(), self.GetGridCursorCol())
        self.GetTable().filter_by(self.GetGridCursorCol(), value)

    def on_remove_filter(self, evt=None):
        self.GetTable().remove_filter()

    def fuzzy_filter(self, *args, **kw):
        self.GetTable().fuzzy_filter(*args, **kw)

    def real_selection(self):
        """
        wxGrid selection is too flexible, we really just need these
        coordinates. This handles all that mess and returns the endpoints ready
        to apply to a range.
        """
        top, left, bottom, right = [0, 0, 0, 0]

        if self.GetSelectionBlockTopLeft():
            top, left = self.selection_top_left()
            bottom, right = self.selection_bottom_right()
        elif self.GetSelectedCols():
            top = 0
            bottom = self.GetNumberRows()
            left, right = self.GetSelectedCols()[0], self.GetSelectedCols()[-1] + 1
        elif self.GetSelectedRows():
            top, bottom = self.GetSelectedRows()[0], self.GetSelectedRows()[-1] + 1
            left = 0
            right = self.GetNumberCols()
        else:
            top, bottom = self.GetGridCursorRow(), self.GetGridCursorRow() + 1
            left, right = self.GetGridCursorCol(), self.GetGridCursorCol() + 1

        single = (top == bottom - 1) and (left == right - 1)
        return [top, bottom, left, right, single]

    def selection_top_left(self):
        """
        Bug! Prevents me from accessing GridCellCoords directly.
        This gets the values as strings and maps the digits to an
        array of ints.
            GridCellCoordsArray: [GridCellCoords(2, 0)]
        https://groups.google.com/forum/#!topic/wxpython-dev/Isw1L5_i6po
        """
        return map(int, re.findall('\d+', str(self.GetSelectionBlockTopLeft())))

    def selection_bottom_right(self):
        """
        Bug! Prevents me from accessing GridCellCoords directly.
        This gets the values as strings and maps the digits to an
        array of ints.
            GridCellCoordsArray: [GridCellCoords(2, 0)]
        https://groups.google.com/forum/#!topic/wxpython-dev/Isw1L5_i6po
        """
        return map(lambda x: int(x) + 1, re.findall('\d+', str(self.GetSelectionBlockBottomRight())))

    def on_copy(self, evt):
        with tempfile.TemporaryFile('w+') as file:
            writer = csv.writer(file, dialect=DEFAULT_COPY_DIALECT)

            top, bottom, left, right, single_cell = self.real_selection()

            if self.GetParent().copy_headers():
                writer.writerow([h for h in self.table.headers[left:right]])

            for r in range(top, bottom):
                row = []
                for c in range(left, right):
                    row.append(self.GetCellValue(r, c))
                writer.writerow(row)

            file.seek(0)

            if wx.TheClipboard.Open():
                clipData = wx.TextDataObject()
                if single_cell:
                    clipData.SetText(file.read().strip())
                else:
                    clipData.SetText(file.read())
                wx.TheClipboard.SetData(clipData)
                wx.TheClipboard.Close()
            else:
                dlg = wx.MessageDialog(self, 'Could not open the clipboard for copying.\nUnknown error :(', 'Clipboard Error', wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()

    def reset_view(self):
        self.AdjustScrollbars()
        self.ForceRefresh()
        self.GetParent().PostSizeEvent()

    def bind_motions(self):
        self.Bind(key_bindings.EVT_MOVE_DOWN, lambda(evt): self.MoveCursorDown(False))
        self.Bind(key_bindings.EVT_MOVE_UP, lambda(evt): self.MoveCursorUp(False))
        self.Bind(key_bindings.EVT_MOVE_LEFT, lambda(evt): self.MoveCursorLeft(False))
        self.Bind(key_bindings.EVT_MOVE_RIGHT, lambda(evt): self.MoveCursorRight(False))
        # ID_MOVE_UP = wx.NewId()
        # ID_MOVE_DOWN = wx.NewId()
        # ID_MOVE_LEFT = wx.NewId()
        # ID_MOVE_RIGHT = wx.NewId()
        # ID_MOVE_PAGE_UP = wx.NewId()
        # ID_MOVE_PAGE_DOWN = wx.NewId()
        # ID_MOVE_SCROLL_UP = wx.NewId()
        # ID_MOVE_SCROLL_DOWN = wx.NewId()

    def on_key_down(self, evt=None):
        if vim.on_key_down(self, evt):
            pass
        else:
            # let original handler take it
            evt.Skip()
