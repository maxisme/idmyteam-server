import os

from settings import functions, config


class DBHelper(object):
    def __init__(self):
        self.conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        if not self.conn:
            print('Error with db connection')
            quit()

    def execute_sql_in_file(self, file):
        x = self.conn.cursor()
        if not os.path.isfile(file):
            raise Exception('No such file %s', file)
        sql = open(file, 'r').read()
        try:
            x.execute(sql)
        except Exception as e:
            print(sql)
        finally:
            x.close()

    def init_schema(self, ROOT_DIR):
        self.execute_sql_in_file(ROOT_DIR + "/db/schema.sql")
