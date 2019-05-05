import re

from settings import functions, config

TABLE = 'idmyteam'
conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])

x = conn.cursor()
x.execute("SELECT table_name FROM information_schema.tables where table_schema='{}';".format(TABLE))
results = x.fetchall()
x.close()


x = conn.cursor()
schema = 'SET FOREIGN_KEY_CHECKS=0;'
for result in results:
    try:
        x.execute("show create table " + result[0])
        scheme = x.fetchall()[0][1]
    except:
        continue

    t = 'table'
    if 'ALGORITHM' in scheme:
        t = 'view'
    schema += 'DROP {} IF EXISTS `{}`;\n{}; \n'.format(t, result[0], scheme)
schema += 'SET FOREIGN_KEY_CHECKS=1;'

schema = schema.replace('DEFINER=`{}`@`localhost` '.format(config.DB["db"]), '')
schema = re.sub(r"AUTO_INCREMENT=\d. ", '', schema)  # remove AUTO_INCREMENT
print(schema)