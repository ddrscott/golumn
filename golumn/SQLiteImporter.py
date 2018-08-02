import logging
import sqlite3
import sys
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SQLiteImporter():
    def __init__(self, headers, db=None, table=None):
        self.table = table
        self.headers = headers
        self.insert_stmt = 'INSERT INTO {0} VALUES ({1})'.format(self.table, ', '.join(['?' for h in self.headers]))
        self.conn = sqlite3.connect(db)

    def create_table(self, rows, column_types):
        query = 'DROP TABLE IF EXISTS {0}'.format(self.table)
        self.conn.execute(query)
        columns = ', '.join([' '.join(('`{0}`'.format(x), y)) for x, y in zip(self.headers, column_types)])
        query = 'CREATE TABLE {0} ({1})'.format(self.table, columns)
        logger.debug(query)
        self.conn.execute(query)
        self.insert(rows)
        self.conn.commit()

    def insert(self, rows):
        try:
            len_headers = len(self.headers)
            sized_rows = [row[:len_headers] + [None for _ in range(len_headers - len(row))] for row in rows]
            self.conn.executemany(self.insert_stmt, sized_rows)
            self.conn.commit()
        except sqlite3.ProgrammingError as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tmp = traceback.format_exception(exc_type, exc_value, exc_traceback)
            exception = "".join(tmp)
            logger.error('Could not insert rows due to {0}'.format(exception))
            logger.debug('Could not insert rows: {0}'.format(repr(rows)))

    def close(self):
        self.conn.close()
