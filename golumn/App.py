import pickle
import os
import sys
import socket
import tempfile
import threading
import traceback
import wx
import wx.grid

from golumn.SQLiteGrid import SQLiteGrid as CreateGrid
import golumn.Utils as Utils

HOST = 'localhost'
PORT = 65430

ID_FILTER_BY_SELECTION = wx.NewId()
ID_REMOVE_FILTER = wx.NewId()
ID_DEBUG_CONSOLE = wx.NewId()


# assign data adapter
def database_path():
    import os
    from os.path import normpath, isdir, join
    data_dir = wx.StandardPaths.Get().GetUserLocalDataDir()
    if not isdir(data_dir):
        os.mkdir(data_dir)
    return normpath(join(data_dir, 'sqlite3_csv_tables.db'))


class GolumnFrame(wx.Frame):
    def __init__(self, *args, **kw):
        self.src = kw.pop('src')

        wx.Frame.__init__(self, *args, **kw)
        self.MakeMenuBar()
        self.MakeToolBar()
        self.MakeStatusBar()
        self.MakeGrid()

    def MakeGrid(self):
        try:
            # Setup the grid BEFORE the frame
            self.grid = CreateGrid(self, self.src)
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
        mb.Append(editMenu, "&Edit")

        # setup Edit menu
        dataMenu = wx.Menu()
        dataMenu.Append(wx.ID_FIND, "&Find\tCtrl+F")
        self.Bind(wx.EVT_MENU, self.on_find, id=wx.ID_FIND)
        dataMenu.AppendSeparator()
        dataMenu.Append(wx.ID_SORT_ASCENDING, "Sort &A to Z\tShift+Ctrl+A")
        dataMenu.Append(wx.ID_SORT_DESCENDING, "Sort &Z to A\tShift+Ctrl+Z")
        dataMenu.Append(ID_REMOVE_FILTER, "&Remove Sort and Filter\tShift+Ctrl+R")
        dataMenu.AppendSeparator()
        dataMenu.Append(ID_FILTER_BY_SELECTION, "Filter by &Selection\tShift+Ctrl+S")
        mb.Append(dataMenu, "&Data")

        # setup Edit menu
        viewMenu = wx.Menu()
        viewMenu.Append(wx.ID_ZOOM_IN, "Zoom In\tCtrl++")
        viewMenu.Append(wx.ID_ZOOM_OUT, "Zoom Out\tCtrl+-")
        viewMenu.Append(wx.ID_ZOOM_100, "Zoom Reset\tCtrl+0")
        mb.Append(viewMenu, "&View")

        # finally assign it to the frame
        self.SetMenuBar(mb)

    def MakeToolBar(self):
        TBFLAGS = (wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)
        tb = self.CreateToolBar(TBFLAGS)
        tb.AddStretchableSpace()
        self.cbLive = wx.CheckBox(tb, -1, "Live")
        self.cbLive.SetValue(True)
        self.cbRegexp = wx.CheckBox(tb, -1, "Regexp")
        self.cbRegexp.SetValue(True)
        self.search = wx.ComboBox(tb, size=(180, -1), style=wx.TE_PROCESS_ENTER)

        tb.AddControl(self.cbLive)
        # TODO: put back regexp once we figure out how to reliably do it in sqlite
        # tb.AddControl(self.cbRegexp)
        tb.AddControl(self.search)
        self.Bind(wx.EVT_CHECKBOX, self.on_live_toggle, self.cbLive)
        self.Bind(wx.EVT_CHECKBOX, self.on_filter_key, self.cbRegexp)

        self.search.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.search.Bind(wx.EVT_TEXT_ENTER, self.on_filter_key)
        self.search.Bind(wx.EVT_TEXT, self.on_filter_key)

        tb.Realize()

    def MakeStatusBar(self):
        self.CreateStatusBar(2)
        self.set_status_text('Loading...')

    def set_status_text(self, text):
        size = wx.Window.GetTextExtent(self, text)
        gripper_size = 6
        self.SetStatusWidths([-1, size.width + gripper_size])
        self.SetStatusText(text, 1)

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
        if self.cbLive.Value:
            self.search.Bind(wx.EVT_TEXT, self.on_filter_key)
            self.on_filter_key()
            # self.grid.fuzzy_filter(self.search.Value, regexp=self.cbRegexp.Value)
        else:
            self.search.Unbind(wx.EVT_TEXT)

    def on_filter_key(self, evt=None):
        if len(self.search.Value) > 0:
            # if self.cbRegexp.Value:
            #     self.grid.fuzzy_filter(regexp=self.search.Value)
            # else:
            self.grid.fuzzy_filter(like=self.search.Value + '%')
        else:
            self.grid.fuzzy_filter(like=None)

    def on_close(self, evt=None):
        self.Close()
        self.Destroy()

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


class GolumnApp(wx.App):
    def OnInit(self):
        self.SetAppName('Golumn')
        if self.CheckServer():
            return False
        else:
            self.SocketServer()
        return True

    def OnExit(self):
        # print "OnExit called"
        return wx.App.OnExit(self)

    def OpenPath(self, title, file_path):
        size = (1024, 600)
        # start window on the top, and demote it in the next cycle
        frm = GolumnFrame(None,
                          style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP,
                          title=title or file_path,
                          size=size,
                          src=file_path,
                          )

        Utils.center_on_active_display(frm, size)
        frm.Show()

        # bounce app icon
        frm.RequestUserAttention()
        # allow the window to go away
        wx.CallLater(1, lambda: frm.SetWindowStyle(wx.DEFAULT_FRAME_STYLE))

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
