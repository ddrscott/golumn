__version__ = '0.8.1'

from collections import OrderedDict
import golumn.events as events

AGGREGATES = OrderedDict([('Sum', events.AggSum),
                          ('Avg', events.AggAvg),
                          ('Count', events.AggCount)])
