import csv
import pickle
import os
import socket
import tempfile
import threading
import wx
import wx.aui
import wx.grid
import wx.lib.newevent

from wx.adv import TaskBarIcon as TaskBarIcon

import ArrayGrid
import golumn.images as images

NewCopyEvent, EVT_COPY_EVENT = wx.lib.newevent.NewEvent()

HOST = 'localhost'
PORT = 65430

ID_FILTER_BY_SELECTION = wx.NewId()
ID_REMOVE_FILTER = wx.NewId()

class GolumnFrame(wx.Frame):
    def __init__(self, *args, **kw):
        rows = kw.pop('rows')
        wx.Frame.__init__(self, *args, **kw)
        self.MakeMenuBar()

        # Setup the grid BEFORE the frame
        self.grid = ArrayGrid.ArrayGrid(self, rows)
        self.grid.SetRowLabelSize(len(str(len(rows))) * 10)
        self.grid.Fit()

        # force scrollbars to redraw
        self.PostSizeEvent()

    def MakeMenuBar(self):
        mb = wx.MenuBar()

        # setup File menu
        fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_OPEN, "&Open\tCtrl+O")
        self.Bind(wx.EVT_MENU, self.on_open, id=wx.ID_OPEN)
        fileMenu.Append(wx.ID_EXECUTE, "&Debug Console\tCtrl+D")
        self.Bind(wx.EVT_MENU, self.on_debug, id=wx.ID_EXECUTE)
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

    def on_debug(self, evt=None):
        def binding_pry():
            import code
            code.interact(local=dict(globals(), **locals()))

        t = threading.Thread(target=binding_pry)
        t.start()

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
            paths = dlg.GetPaths()
            path = paths[0]

            with open(path, 'rb') as input_file:
                title = os.path.basename(path)
                wx.GetApp().LoadFile(title, input_file)

        dlg.Destroy()


class MyTaskBarIcon(TaskBarIcon):
    def __init__(self, frame):
        TaskBarIcon.__init__(self, wx.adv.TBI_DOCK)
        self.frame = frame

        # Set the image
        icon = self.MakeIcon(images.AppIcon.GetImage())
        self.SetIcon(icon, "Golumn")

    def MakeIcon(self, img):
        if "wxMSW" in wx.PlatformInfo:
            img = img.Scale(16, 16)
        elif "wxGTK" in wx.PlatformInfo:
            img = img.Scale(22, 22)
        else:
            img = img.Scale(128, 128)
        # wxMac can be any size upto 128x128, so leave the source img alone....
        icon = wx.Icon(img.ConvertToBitmap())
        return icon


class GolumnApp(wx.App):
    def OnInit(self):
        self.SetAppName('Golumn')
        if self.CheckServer():
            return False
        else:
            self.SocketServer()
        self.task_bar_icon = MyTaskBarIcon(self)
        return True

    def OnExit(self):
        # print "OnExit called"
        return wx.App.OnExit(self)

    def LoadData(self, title, rows):
        title_with_rows = '{} - rows: {:,}'.format(title, len(rows))
        # start window on the top, and demote it in the next cycle
        frm = GolumnFrame(None, style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP, title=title_with_rows, size=(640, 400), rows=rows)
        frm.Centre()
        frm.Show()

        # allow the window to go away
        frm.RequestUserAttention()
        wx.CallLater(1, lambda: frm.ToggleWindowStyle(wx.STAY_ON_TOP))

    def LoadFile(self, title, input_file):
        rows = []
        # detect file type
        dialect = csv.Sniffer().sniff(input_file.read(1024 * 50))
        input_file.seek(0)
        csvreader = csv.reader(input_file, dialect)

        # convert csv reader to rows
        for row in csvreader:
            rows.append(row)

        self.LoadData(title, rows)

    def LoadPath(self, title, file_path):
        with open(file_path, 'rb') as src:
            title = title or os.path.basename(file_path)
            self.LoadFile(title, src)

    def LoadPackage(self, args):
        wx.CallAfter(self.LoadPath, args.title, args.filename)

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
