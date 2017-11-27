import sqlite3


class SQLiteImporter():
    def __init__(self, headers, db=None, table=None):
        self.db = db
        self.table = table
        self.headers = headers
        self.built_table = False

    def insert(self, rows, conn=None):
        self.conn = conn or sqlite3.connect(self.db)
        if not self.built_table:
            self.built_table = True
            self.insert_stmt = self.build_table(rows)
        self.conn.executemany(self.insert_stmt, rows)
        self.conn.commit()

    def build_table(self, rows):
        # TODO: infer types
        self.conn.execute('DROP TABLE IF EXISTS {0}'.format(self.table))
        self.conn.execute('CREATE TABLE {0} ({1})'.format(self.table, ', '.join(self.headers)))
        return 'INSERT INTO {0} VALUES ({1})'.format(self.table, ', '.join(['?' for h in self.headers]))

    def close(self):
        self.conn.close()
