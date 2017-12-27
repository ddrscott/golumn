import wx
import golumn


class DelimiterChoice(wx.Choice):
    def __init__(self, parent, **kw):
        wx.Choice.__init__(self, parent, choices=self.labels(), **kw)

    def labels(self):
        return [label for label, dialect in golumn.DELIMITERS.values()]

    def dialects(self):
        return [dialect for label, dialect in golumn.DELIMITERS.values()]

    def values_list(self):
        return [v for v in golumn.DELIMITERS.values()]

    def value_at(self, i):
        return [v for v in golumn.DELIMITERS.values()][i]

    def selected_dialect(self):
        selected = self.value_at(self.Selection)
        return selected[1]

    def selected_label(self):
        selected = self.value_at(self.Selection)
        return selected[0]
