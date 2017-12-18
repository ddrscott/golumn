import wx


class WindowMenu(wx.Menu):
    def __init__(self, frame, *args, **kw):
        wx.Menu.__init__(self, *args, **kw)
        frame.Bind(wx.EVT_ACTIVATE, self.on_activate_window)
        frame.Bind(wx.EVT_CLOSE, self.on_close_window)
        self.frame = frame

    def on_close_window(self, evt):
        self.frame.Unbind(wx.EVT_CLOSE, handler=self.on_close_window)
        self.frame.Unbind(wx.EVT_ACTIVATE, handler=self.on_activate_window)
        self.frame._wx_mac_window_menu__frame_closing = True
        other_active_window = [w for w in wx.GetTopLevelWindows() if not w == self.frame and w.IsActive()]
        if not self.frame.IsActive() and len(other_active_window) > 0:
            self.frame.Raise()
            for w in other_active_window:
                wx.CallAfter(lambda: w.Raise())
        evt.Skip()

    def on_activate_window(self, evt):
        self.clear()
        self.rebuild_menu_items(evt.GetId(), evt.Active)
        evt.Skip()

    def rebuild_menu_items(self, window_id, active):
        open_windows = [w for w in wx.GetTopLevelWindows() if not (hasattr(w, '_wx_mac_window_menu__frame_closing'))]
        for i, w in enumerate(open_windows):
            shortcut = "\tCTRL+{0}".format(i+1) if i < 9 else ''
            item = self.AppendRadioItem(w.Id, w.Title + shortcut)
            self.Check(item.Id, window_id == w.Id and active)
        if active:
            self.Bind(wx.EVT_MENU, self.on_selected)
        else:
            self.Unbind(wx.EVT_MENU)

    def on_selected(self, evt=None):
        evt.Skip()
        selected_window = wx.FindWindowById(evt.GetId())
        wx.CallAfter(lambda: selected_window.Raise())

    def clear(self):
        for m in self.GetMenuItems():
            self.Remove(m)
            m.Destroy()


def test():
    app = wx.App()
    for i in range(1, 11):
        frm = wx.Frame(None, title="Frame #{0}".format(i), size=(300, 300))
        mb = wx.MenuBar()
        window_menu = WindowMenu(frame=frm)
        mb.Append(window_menu, "&Window #{0}".format(i))
        frm.SetMenuBar(mb)
        frm.SetPosition((i * 24 + 350, i * 24 + 150))
        frm.Show()
    app.MainLoop()


if __name__ == '__main__':
    test()
