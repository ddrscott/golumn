"""Simple log wrapper to write to syslog with the context of the executable name.
"""
import __main__
import syslog
import os

# set the context to the executable name
syslog.openlog(os.path.basename(__main__.__file__))


def log(txt, lvl=syslog.LOG_NOTICE):
    syslog.syslog(lvl, txt)
