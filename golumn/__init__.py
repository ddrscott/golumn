__version__ = '0.10.0'

from collections import OrderedDict
import golumn.events as events

AGGREGATES = OrderedDict([('Sum', events.AggSum),
                          ('Avg', events.AggAvg),
                          ('Count', events.AggCount)])
