import csv
import re
import wx
import tempfile

import golumn
import golumn.App
import golumn.Utils as Utils
from golumn.SQLiteTable import SQLiteTable
import golumn.events as events
import golumn.key_bindings as key_bindings
import golumn.key_bindings.vim as vim

DEFAULT_COPY_DIALECT = 'excel-tab'

# https://github.com/wxWidgets/wxWidgets/blob/4d4c14cd656734ca42b6e845618e1a46398436ed/src/generic/grid.cpp#L8480
COLUMN_PADDING = 10

# https://github.com/wxWidgets/wxWidgets/blob/4d4c14cd656734ca42b6e845618e1a46398436ed/src/generic/grid.cpp#L8482
ROW_PADDING = 6

# Percentage factor of windows width
MAX_COLUMN_WIDTH_PCT = 0.9

MAX_FONT_SIZE = 200.0

MIN_FONT_SIZE = 1.0

ZOOM_INCREMENT = 1.2


class SQLiteGrid(wx.grid.Grid):
    def __init__(self, parent, src):
        self.src = src
        self.force_grid_cursor = False
        wx.grid.Grid.__init__(self)
        self.Create(parent)
        self.EnableEditing(False)

        self.default_font_size = 12
        self.font_size = self.default_font_size

        self.SetColLabelSize(self.font_size + 8)
        self.SetRowLabelSize(self.font_size + 18)
        self.SetMargins(-10, -10)   # remove some whitespace, but leave enough for scrollbar overlap
        self.DisableDragRowSize()
        self.SetUseNativeColLabels()
        self.bind_copy_menu()
        self.bind_delimiter()
        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        parent.Bind(wx.EVT_MENU, self.on_copy, id=wx.ID_COPY)
        parent.Bind(wx.EVT_MENU, self.on_sort_a, id=wx.ID_SORT_ASCENDING)
        parent.Bind(wx.EVT_MENU, self.on_sort_z, id=wx.ID_SORT_DESCENDING)
        parent.Bind(wx.EVT_MENU, self.on_remove_filter, id=events.EVT_REMOVE_FILTER)
        parent.Bind(wx.EVT_MENU, self.on_filter_selection, id=events.EVT_FILTER_SELECTION)
        parent.Bind(wx.EVT_MENU, self.on_exclude_selection, id=events.EVT_EXCLUDE_SELECTION)
        parent.Bind(wx.EVT_MENU, self.on_zoom_in, id=wx.ID_ZOOM_IN)
        parent.Bind(wx.EVT_MENU, self.on_zoom_out, id=wx.ID_ZOOM_OUT)
        parent.Bind(wx.EVT_MENU, self.on_zoom_reset, id=wx.ID_ZOOM_100)

        # bind to aggregate selection
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_CLICK, self.on_label_left_click)
        self.Bind(wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.on_label_right_click)
        self.Bind(wx.grid.EVT_GRID_COL_SORT, self.on_grid_col_sort)

        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_cell_right_click)
        self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.on_calc_aggregates)
        self.bind_motions()

        wx.CallAfter(self.init_table, src)

    def init_table(self, src, dialect=None):
        self.table = SQLiteTable(src=src, dst_db=golumn.App.database_path(), dialect=dialect)
        self.SetTable(self.table, False)
        for i, ct in enumerate(self.table.column_types):
            if ct == 'numeric' or ct == 'integer':
                attr = wx.grid.GridCellAttr()
                attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
                self.SetColAttr(i, attr)
        if not dialect:
            self.update_ch_delimiter()
        self.auto_size_visible_rows()

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
        parent.set_aggregate_text(agg_text)

    def on_label_right_click(self, evt=None):
        evt.Skip()

    def on_label_left_click(self, evt=None):
        self.table.force_value = 'selection'
        self.SelectCol(evt.GetCol())
        self.table.force_value = None

    def on_grid_col_sort(self, evt=None):
        if self.IsSortOrderAscending():
            self.SetSortingColumn(evt.GetCol(), ascending=True)
            self.GetTable().SortColumn(evt.GetCol(), reverse=False)
        else:
            self.SetSortingColumn(evt.GetCol(), ascending=False)
            self.GetTable().SortColumn(evt.GetCol(), reverse=True)

    def on_zoom_in(self, evt=None):
        self.font_size = min(self.font_size * ZOOM_INCREMENT, MAX_FONT_SIZE)
        self.reset_font()

    def on_zoom_out(self, evt=None):
        self.font_size = max(self.font_size / ZOOM_INCREMENT, MIN_FONT_SIZE)
        self.reset_font()

    def on_zoom_reset(self, evt=None):
        self.font_size = self.default_font_size
        self.reset_font()

    def reset_font(self):
        self.SetDefaultCellFont(wx.Font(wx.FontInfo(int(round(self.font_size)))))
        self.auto_size_visible_rows()
        self.reset_view()

    def on_select_cell(self, evt=None):
        if self.force_grid_cursor:
            self.force_grid_cursor = False
        else:
            self.force_grid_cursor = True
            wx.CallAfter(self.SetGridCursor, evt.GetRow(), evt.GetCol())

    def bind_copy_menu(self):
        self.Bind(wx.EVT_MENU, self.on_sort_a, id=events.EVT_SORT_A)
        self.Bind(wx.EVT_MENU, self.on_sort_z, id=events.EVT_SORT_Z)
        self.Bind(wx.EVT_MENU, self.on_filter_selection, id=events.EVT_FILTER_SELECTION)
        self.Bind(wx.EVT_MENU, self.on_exclude_selection, id=events.EVT_EXCLUDE_SELECTION)
        self.Bind(wx.EVT_MENU, self.on_remove_filter, id=events.EVT_REMOVE_FILTER)
        parent = self.GetParent()
        parent.Bind(wx.EVT_MENU, self.on_menu_copy_with_headers, id=events.EVT_MENU_COPY_WITH_HEADER)
        parent.Bind(wx.EVT_MENU, self.on_menu_copy_as_sql_in, id=events.EVT_MENU_COPY_AS_SQL_IN)
        parent.Bind(wx.EVT_MENU, self.on_menu_copy_as_ruby_array, id=events.EVT_MENU_COPY_AS_RUBY_ARRAY)

    def bind_delimiter(self):
        parent = self.GetParent()
        parent.ch_delimiter.Bind(wx.EVT_CHOICE, self.on_choice_delimiter)

    def update_ch_delimiter(self):
        idx = Utils.index_of(golumn.DELIMITERS.keys(), self.table.dialect.delimiter)
        if idx:
            parent = self.GetParent()
            parent.ch_delimiter.SetSelection(idx)

    def on_choice_delimiter(self, evt):
        parent = self.GetParent()
        self.init_table(self.src, dialect=parent.ch_delimiter.selected_dialect())

    def on_menu_copy_with_headers(self, evt):
        self.copy_as_excel(with_headers=True)

    def on_menu_copy_as_sql_in(self, evt):
        self.copy_as_sql_in()

    def on_menu_copy_as_ruby_array(self, evt):
        self.copy_as_ruby_array()

    def on_cell_right_click(self, evt=None):
        self.SetGridCursor(evt.GetRow(), evt.GetCol())

        # make a menu
        menu = wx.Menu()
        # Show how to put an icon in the menu
        menu.Append(events.EVT_SORT_A, "Sort &A..Z\tShift+Ctrl+A")
        menu.Append(events.EVT_SORT_Z, "Sort &Z..A\tShift+Ctrl+Z")
        menu.AppendSeparator()

        # filter items
        menu.Append(events.EVT_FILTER_SELECTION, "Filter by &Selection\tShift+Ctrl+S")
        menu.Append(events.EVT_EXCLUDE_SELECTION, "&Exclude Selection\tShift+Ctrl+E")
        menu.Append(events.EVT_REMOVE_FILTER, "&Remove Sort and Filter\tShift+Ctrl+R")
        menu.AppendSeparator()

        # copy menu
        parent = self.GetParent()
        menu.AppendSubMenu(parent.create_copy_menu(), "&Copy Special")
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

    def on_exclude_selection(self, evt=None):
        value = self.GetCellValue(self.GetGridCursorRow(), self.GetGridCursorCol())
        self.GetTable().exclude_by(self.GetGridCursorCol(), value)

    def on_remove_filter(self, evt=None):
        self.GetTable().remove_filter()
        # remove sort indicators
        self.UnsetSortingColumn()

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
        self.copy_as_excel(with_headers=self.GetParent().copy_headers())

    def selection_as_array(self, quote):
        top, bottom, left, right, single_cell = self.real_selection()
        values = []
        for r in range(top, bottom):
            for c in range(left, right):
                v = self.GetCellValue(r, c)
                ct = self.table.column_types[c]
                if ct == 'numeric' or ct == 'integer':
                    values.append(str(v))
                else:
                    values.append(quote + v + quote)
        return values

    def set_clipboard(self, text):
        if wx.TheClipboard.Open():
            clipData = wx.TextDataObject()
            clipData.SetText(text)
            wx.TheClipboard.SetData(clipData)
            wx.TheClipboard.Close()
        else:
            dlg = wx.MessageDialog(self, 'Could not open the clipboard for copying.\nUnknown error :(', 'Clipboard Error', wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()

    def copy_as_sql_in(self):
        values = self.selection_as_array(quote="'")
        self.set_clipboard('(' + ', '.join(values) + ')')

    def copy_as_ruby_array(self):
        values = self.selection_as_array(quote="'")
        self.set_clipboard('[' + ', '.join(values) + ']')

    def copy_as_excel(self, with_headers=False, mode=None):
        with tempfile.TemporaryFile('w+') as file:
            writer = csv.writer(file, dialect=DEFAULT_COPY_DIALECT)

            top, bottom, left, right, single_cell = self.real_selection()

            if with_headers:
                writer.writerow([h for h in self.table.headers[left:right]])

            for r in range(top, bottom):
                row = []
                for c in range(left, right):
                    row.append(self.GetCellValue(r, c))
                writer.writerow(row)

            file.seek(0)

            if single_cell:
                self.set_clipboard(file.read().strip())
            else:
                self.set_clipboard(file.read())

    def reset_view(self):
        self.AdjustScrollbars()
        self.ForceRefresh()
        self.GetParent().PostSizeEvent()

    def bind_motions(self):
        self.Bind(key_bindings.EVT_MOVE_DOWN, lambda evt: self.MoveCursorDown(False))
        self.Bind(key_bindings.EVT_MOVE_UP, lambda evt: self.MoveCursorUp(False))
        self.Bind(key_bindings.EVT_MOVE_LEFT, lambda evt: self.MoveCursorLeft(False))
        self.Bind(key_bindings.EVT_MOVE_RIGHT, lambda evt: self.MoveCursorRight(False))

    def on_key_down(self, evt=None):
        if vim.on_key_down(self, evt):
            pass
        elif evt.ShiftDown() and evt.GetKeyCode() == 59:  # 'Shift-;, :'
            wx.CallAfter(self.on_super_key)
            evt.Skip()
        else:
            # let original handler take it
            evt.Skip()

    def visible_rows(self):
        ux, uy = self.GetScrollPixelsPerUnit()
        sx, sy = self.GetViewStart()
        w, h = self.GridWindow.ClientSize
        sx *= ux
        sy *= uy
        x0 = self.XToCol(sx)
        y0 = self.YToRow(sy)
        x1 = self.XToCol(sx + w)
        y1 = self.YToRow(sy + h)
        if y1 < 0 and y0 >= 0:
            y1 = self.GetNumberRows()
        return ((x0, y0), (x1, y1))

    # GetBestSize logic borrowed from:
    #   https://github.com/wxWidgets/wxWidgets/blob/4d4c14cd656734ca42b6e845618e1a46398436ed/src/generic/grid.cpp#L8349
    def auto_size_visible_rows(self):
        """
        Similar to `AutoSize` but uses `SetDefaultRowSize` instead of `SetRowSize`.
        """
        dc = wx.ClientDC(self.GridWindow)
        max_columns = [0 for c in range(0, self.GetNumberCols())]
        max_row = 0
        visible_rows = self.visible_rows()
        for c in range(0, self.GetNumberCols()):
            for r in range(visible_rows[0][1], visible_rows[1][1]):
                attr = self.GetOrCreateCellAttr(r, c)
                rend = self.GetCellRenderer(r, c)
                if rend is not None:
                    size = rend.GetBestSize(self, attr, dc, r, c)
                    max_columns[c] = max(max_columns[c], size[0])
                    max_row = max(max_row, size[1])

        max_column_width = self.GridWindow.Size[0] * MAX_COLUMN_WIDTH_PCT

        # check width of all the column labels
        for c in range(0, self.GetNumberCols()):
            dc.SetFont(self.GetLabelFont())
            value = self.GetColLabelValue(c)
            size = dc.GetTextExtent(value)
            width = size[0] + ROW_PADDING
            max_columns[c] = min(max(max_columns[c], width), max_column_width)

        self.BeginBatch()
        for c in range(0, self.GetNumberCols()):
            self.SetColSize(c, max_columns[c] + COLUMN_PADDING)
        self.SetDefaultRowSize(max_row + ROW_PADDING, resizeExistingRows=True)
        self.EndBatch()
        self.MakeCellVisible(visible_rows[0][1], visible_rows[0][0])

    def on_super_key(self):
        # self.Scroll(-1, 100)
        # self.GridWindow.ScrollWindow(10, 10)
        self.debug_in_thread()

    def debug_in_thread(self):
        from ptpython.repl import embed
        import threading
        t = threading.Thread(target=embed, args=(globals(), locals()))
        t.setDaemon(True)
