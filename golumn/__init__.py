__version__ = '0.20.0'
from collections import OrderedDict
import csv
from copy import copy

bar = copy(csv.excel_tab)
bar.delimiter = '|'

DELIMITERS = OrderedDict([
    (',', (', comma', csv.excel)),
    ('\t', ('\\t tab', csv.excel_tab)),
    ('|', ('| bar', bar))
])
