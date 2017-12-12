"""Simple log wrapper to write to syslog with the context of the executable name.
"""
import syslog
import wx

# set the context to the executable name
context_name = None


def log(txt, lvl=syslog.LOG_NOTICE):
    global context_name
    if context_name is None:
        app = wx.GetApp()
        context_name = app and app.GetAppName()
    syslog.openlog(str(context_name))
    syslog.syslog(lvl, txt)
    wx.LogDebug(txt)
