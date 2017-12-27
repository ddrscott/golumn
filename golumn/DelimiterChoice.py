import wx
import golumn


class DelimiterChoice(wx.Choice):
    def __init__(self, parent, **kw):
        wx.Choice.__init__(self, parent, choices=self.labels(), **kw)

    def labels(self):
        return [label for label, dialect in golumn.DELIMITERS.values()]

    def dialects(self):
        return [dialect for label, dialect in golumn.DELIMITERS.values()]

    def selected_dialect(self):
        selected = golumn.DELIMITERS.values()[self.Selection]
        print("!!!!!!", selected)
        return selected[1]

    def selected_label(self):
        selected = golumn.DELIMITERS.values()[self.Selection]
        return selected[0]
