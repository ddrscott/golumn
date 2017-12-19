"""Simple log wrapper to write to syslog with the context of the executable name.
"""
import syslog
import wx


def log(txt, lvl=syslog.LOG_NOTICE):
    syslog.openlog('golumn')
    syslog.syslog(lvl, txt)
    wx.LogDebug(txt)
