import chardet
import codecs
import os
import re
import wx
from threading import Timer


# Thanks https://gist.github.com/walkermatt/2871026
def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()
        return debounced


def active_display_client_area():
    active_display = wx.Display.GetFromPoint(wx.GetMousePosition())
    return wx.Display(active_display).ClientArea


def center_on_active_display(frm, size):
    active_area = active_display_client_area()
    w1, h1 = size
    x2, y2, w2, h2 = active_area
    x1 = int((w2 - w1) / 2)
    y1 = int((h2 - h1) / 2)
    frm.SetPosition((x2 + x1, y2 + y1))


def unique_array(items):
    """
    If an item is duplicated, it appends a numeric suffix to it.
        f(items=(a, b, a, c)) => (a, b, a1, c)
    """
    counts = dict()
    result = list()
    for i in items:
        counts[i] = counts.get(i, -1) + 1
        result.append(str(i) + str(counts[i]) if counts[i] > 0 else i)
    return result


def size_by_percent(text):
    if text is None or len(text) < 3:
        return None

    m = re.match(r"(\d+)(%)?x(\d+)(%)?", text)
    if m is None:
        return None

    groups = m.groups()

    x, y, w, h = active_display_client_area()
    if groups[1]:
        w = w * (int(groups[0]) / 100.0)
    else:
        w = int(groups[0])

    if groups[3]:
        h = h * (int(groups[2]) / 100.0)
    else:
        h = int(groups[2])

    return (w, h)


# Thanks: https://stackoverflow.com/a/13591421/613772
def detect_encoding(src):
    bytes = min(32, os.path.getsize(src))
    raw = open(src, 'rb').read(bytes)

    if raw.startswith(codecs.BOM_UTF8):
        encoding = 'utf-8-sig'
    else:
        result = chardet.detect(raw)
        encoding = result['encoding']
    if encoding == 'ascii':
        encoding = 'utf-8'
    return encoding


def index_of(list, val):
    """Helper to get the 0 based index of `val` in the `list`
    """
    found = [i for i, k in enumerate(list) if k == val]
    if len(found) > 0:
        return found[0]
    return None

