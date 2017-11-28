import sqlite3


class SQLiteImporter():
    def __init__(self, headers, db=None, table=None):
        self.table = table
        self.headers = headers
        self.insert_stmt = 'INSERT INTO {0} VALUES ({1})'.format(self.table, ', '.join(['?' for h in self.headers]))
        self.conn = sqlite3.connect(db)

    def create_table(self, rows):
        # TODO: infer types
        self.conn.execute('DROP TABLE IF EXISTS {0}'.format(self.table))
        self.conn.execute('CREATE TABLE {0} ({1})'.format(self.table, ', '.join(self.headers)))
        self.insert(rows)
        self.conn.commit()

    def insert(self, rows):
        self.conn.executemany(self.insert_stmt, rows)
        self.conn.commit()

    def close(self):
        self.conn.close()
