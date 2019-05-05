from settings import functions, config


class DBHelper(object):
    def __init__(self):
        self.conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        if not self.conn:
            print('Error with db connection')
            quit()

    def execute_sql_in_file(self, file):
        x = self.conn.cursor()
        sql = open(file, 'r').read()
        x.execute(sql)
        x.close()

    def init_schema(self, ROOT_DIR):
        self.execute_sql_in_file(ROOT_DIR + "/db/schema.sql")
