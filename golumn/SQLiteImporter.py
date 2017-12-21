import wx
import sqlite3
from golumn.log import log


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
        log(query)
        self.conn.execute(query)
        self.insert(rows)
        self.conn.commit()

    def insert(self, rows):
        self.conn.executemany(self.insert_stmt, rows)
        self.conn.commit()

    def close(self):
        self.conn.close()
