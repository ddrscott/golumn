import os
import sys
import csv
import wx
import wx.aui
import wx.grid
import wx.lib.newevent
import ArrayGrid

NewCopyEvent, EVT_COPY_EVENT = wx.lib.newevent.NewEvent()


class GolumnFrame(wx.Frame):
    def __init__(self, *args, **kw):
        wx.Frame.__init__(self, *args, **kw)
        self.MakeMenuBar()

    def MakeMenuBar(self):
        editMenu = wx.Menu()
        editMenu.Append(wx.ID_COPY, "&Copy\tCtrl+C")
        mb = wx.MenuBar()
        mb.Append(editMenu, "&Edit")
        self.SetMenuBar(mb)


class GolumnApp(wx.App):

    def OnInit(self):
        self.SetAppName('Golumn')
        self.frm = GolumnFrame(None, size=(640, 400))
        self.frm.Centre()
        self.frm.Show()
        return True

    def LoadData(self, title, rows):
        # Setup the grid BEFORE the frame
        self.grid = ArrayGrid.ArrayGrid(self.frm, rows)
        self.grid.SetRowLabelSize(len(str(len(rows))) * 8)
        self.grid.Fit()

        # load as frame
        self.frm.SetTitle('{} - rows: {:,}'.format(title, len(rows)))
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
        dialect = csv.Sniffer().sniff(csvfile.read(1024 * 50))
        csvfile.seek(0)
        csvreader = csv.reader(csvfile, dialect)

        # convert csv reader to rows
        for row in csvreader:
            rows.append(row)

    app = GolumnApp(useBestVisual=True)
    app.LoadData(title, rows)
    app.MainLoop()


# if __name__ == '__main__':
#     main()
