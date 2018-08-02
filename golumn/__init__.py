__version__ = '0.21.1'

from collections import OrderedDict
import csv
from copy import copy

bar = copy(csv.excel_tab)
bar.delimiter = '|'

semi = copy(csv.excel_tab)
semi.delimiter = ';'

DELIMITERS = OrderedDict([
    (',', (', comma', csv.excel)),
    ('\t', ('\\t tab', csv.excel_tab)),
    ('|', ('| bar', bar)),
    (';', ('; semi', semi))
])
