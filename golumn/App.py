# -*- coding: utf8 -*-
import logging
import platform
import pickle
import os
import sys
import socket
import tempfile
import threading
import traceback
import wx
import wx.grid

from golumn.SQLiteGrid import SQLiteGrid
from golumn.DelimiterChoice import DelimiterChoice
from golumn.WindowMenu import WindowMenu
import golumn.Utils as Utils
import golumn.events as events

HOST = 'localhost'
PORT = 65430
IN_MEMORY = False

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# assign data adapter
def database_path():
    if IN_MEMORY:
        return "file::memory:?cache=shared"

    import os
    from os.path import normpath, isdir, join
    data_dir = wx.StandardPaths.Get().GetUserLocalDataDir()
    if not isdir(data_dir):
        os.mkdir(data_dir)
    return normpath(join(data_dir, 'sqlite3_csv_tables.db'))


class GolumnFrame(wx.Frame):
    def __init__(self, *args, **kw):
        self.src = kw.pop('src')
        self.in_memory = kw.pop('in_memory', False)
        wx.Frame.__init__(self, *args, **kw)

        self.closing = False

        self.MakeMenuBar()
        self.MakeToolBar()
        self.MakeStatusBar()
        self.MakeGrid()

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_IDLE, self.on_idle)

    def MakeGrid(self):
        try:
            # Setup the grid BEFORE the frame
            self.grid = SQLiteGrid(self, self.src)
            self.PostSizeEvent()
        except Exception as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
            wx.MessageBox("Error: {0}".format(repr(err)), caption="Could not open file: {0}".format(self.src))
            self.Close()

    def MakeMenuBar(self):
        mb = wx.MenuBar()

        # setup File menu
        fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        fileMenu.AppendSeparator()
        fileMenu.Append(wx.ID_CLOSE, "&Close\tCtrl+W")
        self.Bind(wx.EVT_MENU, self.on_close, id=wx.ID_CLOSE)
        mb.Append(fileMenu, "&File")

        # setup Edit menu
        editMenu = wx.Menu()
        editMenu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
        editMenu.AppendSubMenu(self.create_copy_menu(), "Copy Special\tShift+Ctrl+C")
        mb.Append(editMenu, "&Edit")

        # setup Edit menu
        dataMenu = wx.Menu()
        dataMenu.Append(wx.ID_FIND, "&Find\tCtrl+F")
        self.Bind(wx.EVT_MENU, self.on_find, id=wx.ID_FIND)
        dataMenu.AppendSeparator()
        dataMenu.Append(wx.ID_SORT_ASCENDING, "Sort &A to Z\tShift+Ctrl+A")
        dataMenu.Append(wx.ID_SORT_DESCENDING, "Sort &Z to A\tShift+Ctrl+Z")
        dataMenu.Append(events.EVT_REMOVE_FILTER, "&Remove Sort and Filter\tShift+Ctrl+R")
        dataMenu.AppendSeparator()
        dataMenu.Append(events.EVT_FILTER_SELECTION, "Filter by &Selection\tShift+Ctrl+S")
        dataMenu.Append(events.EVT_EXCLUDE_SELECTION, "&Exclude Selection\tShift+Ctrl+E")
        mb.Append(dataMenu, "&Data")

        # setup Edit menu
        viewMenu = wx.Menu()
        viewMenu.Append(wx.ID_ZOOM_IN, "Zoom In\tCtrl++")
        viewMenu.Append(wx.ID_ZOOM_OUT, "Zoom Out\tCtrl+-")
        viewMenu.Append(wx.ID_ZOOM_100, "Zoom Reset\tCtrl+0")
        mb.Append(viewMenu, "&View")

        window_menu = WindowMenu(frame=self)
        mb.Append(window_menu, "&Window")
        # finally assign it to the frame
        self.SetMenuBar(mb)

    def create_copy_menu(self):
        copy_menu = wx.Menu()
        copy_menu.Append(events.EVT_MENU_COPY_WITH_HEADER, "Copy with Headers")
        copy_menu.Append(events.EVT_MENU_COPY_AS_SQL_IN, "Copy as SQL IN")
        copy_menu.Append(events.EVT_MENU_COPY_AS_RUBY_ARRAY, "Copy as Array")
        return copy_menu

    def MakeToolBar(self):
        TBFLAGS = (wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)
        tb = self.CreateToolBar(TBFLAGS)
        self.cb_live_filter = wx.CheckBox(tb, -1, "Live")
        self.cb_live_filter.SetValue(True)
        self.cb_copy_headers = wx.CheckBox(tb, -1, "Copy Headers")
        self.cb_copy_headers.SetValue(False)
        self.cb_keep_on_top = wx.CheckBox(tb, -1, "Keep on Top")
        self.cb_keep_on_top.SetValue(False)
        self.cb_keep_on_top.Bind(wx.EVT_CHECKBOX, self.on_keep_on_top)
        self.ch_delimiter = DelimiterChoice(tb)
        self.cbRegexp = wx.CheckBox(tb, -1, "Regexp")
        self.cbRegexp.SetValue(True)
        self.search = wx.TextCtrl(tb, size=(180, -1), style=wx.TE_PROCESS_ENTER)

        if platform.system() == 'Darwin':
            self.search.SetHint('Filter Rows... (⌘-F)')
        else:
            self.search.SetHint('Filter Rows...')

        tb.AddControl(self.cb_copy_headers)
        tb.AddControl(self.cb_keep_on_top)
        tb.AddStretchableSpace()
        tb.AddControl(wx.StaticText(tb, label='Delimiter'))
        tb.AddControl(self.ch_delimiter)
        tb.AddStretchableSpace()

        tb.AddControl(self.cb_live_filter)
        # TODO: put back regexp once we figure out how to reliably do it in sqlite
        # tb.AddControl(self.cbRegexp)
        tb.AddControl(self.search)
        self.Bind(wx.EVT_CHECKBOX, self.on_live_toggle, self.cb_live_filter)
        self.Bind(wx.EVT_CHECKBOX, self.on_filter_key, self.cbRegexp)

        self.search.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.search.Bind(wx.EVT_TEXT_ENTER, self.on_filter_key)
        self.search.Bind(wx.EVT_TEXT, self.on_filter_key)

        tb.Realize()

    def MakeStatusBar(self):
        self.CreateStatusBar(2)
        self.SetStatusText('Select cells for aggregates.', 0)
        self.set_status_text('Loading...')

    def set_aggregate_text(self, text):
        # size = wx.Window.GetTextExtent(self, text)
        # self.SetStatusWidths([-1, size / 3, self.GetStatusBar().GetStatusWidth(2)])
        self.SetStatusText(text, 0)

    def on_reposition(self):
        del self.size_changed
        return
        rect = self.GetStatusBar().GetFieldRect(1)
        rect.x += 1  # padding
        rect.y += 1
        # self.copy_header_choice.SetRect(rect)

    def set_status_text(self, text):
        size = wx.Window.GetTextExtent(self, text)
        gripper_size = 6
        self.SetStatusWidths([-1, size.width + gripper_size])
        self.SetStatusText(text, 1)

    def copy_headers(self):
        return self.cb_copy_headers.Value

    def on_keep_on_top(self, evt=None):
        if evt is not None:
            evt.Skip()
        self.ToggleWindowStyle(wx.STAY_ON_TOP)

    def on_size(self, evt=None):
        evt.Skip()
        self.size_changed = True
        self.on_reposition()

    def on_idle(self, evt=None):
        if hasattr(self, 'size_changed'):
            self.on_reposition()

    def on_find(self, evt):
        self.search.SetFocus()
        self.search.SelectAll()

    def on_key_down(self, evt=None):
        """
        For some reason, CMD-A for select all is ignored by children of
        TextCtrl eventhough TextCtrl supports it be default. Super annoying.
        This handler fixes it for us.
        """
        keycode = evt.GetKeyCode()
        if keycode == 65 and evt.ControlDown():
            self.search.SelectAll()
        evt.Skip()

    def on_live_toggle(self, evt=None):
        if self.cb_live_filter.Value:
            self.search.Bind(wx.EVT_TEXT, self.on_filter_key)
            self.on_filter_key()
            # self.grid.fuzzy_filter(self.search.Value, regexp=self.cbRegexp.Value)
        else:
            self.search.Unbind(wx.EVT_TEXT)

    def on_filter_key(self, evt=None):
        if len(self.search.Value) > 0:
            self.grid.fuzzy_filter(like=self.search.Value + '%')
        else:
            self.grid.fuzzy_filter(like=None)

    def on_close(self, evt=None):
        self.Close()

    def __del__(self):
        if hasattr(self, 'grid'):
            self.grid.table.clean_up()


    def on_open(self, evt=None):
        # filename = wx.FileSelector("Choose a file to open")
        # return
        dlg = wx.FileDialog(
            self, message="Choose a file to open",
            defaultDir=os.getcwd(),
            defaultFile="",
            wildcard="CSV Files (*.csv)|*.csv",
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST | wx.FD_PREVIEW
        )

        if dlg.ShowModal() == wx.ID_OK:
            for path in dlg.GetPaths():
                wx.GetApp().OpenPath(path, path)

        dlg.Destroy()


def MyExceptionHook(etype, value, trace):
    tmp = traceback.format_exception(etype, value, trace)
    exception = "".join(tmp)
    logger.error(exception)
    wx.MessageBox("Error: {0}".format(exception), caption="Unexpected Error")


sys.threadhook = MyExceptionHook


class GolumnApp(wx.App):
    def OnInit(self):
        self.frm = None
        self.SetAppName('Golumn')
        if self.CheckServer():
            return False
        else:
            self.SocketServer()
        return True

    def OnExit(self):
        # print("OnExit called")
        # if self.frm:
        #     self.frm.on_close()

        return wx.App.OnExit(self)

    def OpenPath(self, title=None, file_path=None, size=None, in_memory=False):
        # FIXME don't use global
        global IN_MEMORY
        IN_MEMORY = in_memory

        size = Utils.size_by_percent(size)
        if size:
            logger.debug("Size: {0}".format(size))
        size = size or (1024, 600)
        # start window on the top, and demote it in the next cycle
        self.frm = GolumnFrame(None,
                          style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP,
                          title=title or file_path,
                          size=size,
                          src=file_path
                          )

        Utils.center_on_active_display(self.frm, size)
        self.frm.Show()

        # bounce app icon
        self.frm.RequestUserAttention()

        # allow the window to go away
        wx.CallAfter(self.AfterStart, self.frm)

    def AfterStart(self, frm):
        frm.SetWindowStyle(wx.DEFAULT_FRAME_STYLE)

    def LoadPackage(self, args):
        wx.CallAfter(self.OpenPath, args.title, args.filename)

    def CheckServer(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            s.close()
            return True
        except socket.error:
            return False

    def SocketServer(self):
        def _server():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((HOST, PORT))
            s.listen(1)
            while 1:
                # print "waiting for accept"
                conn, addr = s.accept()
                # print 'Connected by', addr
                with tempfile.SpooledTemporaryFile() as tmp:
                    while 1:
                        data = conn.recv(1024 * 4)
                        if not data:
                            break
                        tmp.write(data)
                    tmp.seek(0)
                    package = pickle.load(tmp)
                    wx.GetApp().LoadPackage(package['args'])
                # print "closing connection"
                conn.close()
        t = threading.Thread(target=_server)
        t.setDaemon(True)
        t.start()
