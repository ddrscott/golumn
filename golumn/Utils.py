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


def center_on_active_display(frm, size):
    active_display = wx.Display.GetFromPoint(wx.GetMousePosition())
    active_area = wx.Display(active_display).ClientArea
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
