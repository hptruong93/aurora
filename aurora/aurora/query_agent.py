import MySQLdb as mdb
import traceback
import sys
import logging

from aurora import config
LOGGER = logging.getLogger(__name__)

def _database_connection():
        return mdb.connect(config.CONFIG['mysql']['mysql_host'],
                                   config.CONFIG['mysql']['mysql_username'],
                                   config.CONFIG['mysql']['mysql_password'],
                                   config.CONFIG['mysql']['mysql_db'])

def _generate_query(table_name, fields, criteria):
    if len(fields) == 0:
        to_execute = """SELECT * FROM %s""" % table_name
    else:
        to_execute = "SELECT " + ",".join(fields) + " FROM %s" % table_name

    #Now parse the criteria
    if len(criteria) != 0:
        to_execute += " WHERE "
        to_execute += " AND ".join(criteria)
    return to_execute

def join_table(table1, table2, field1, field2, type = "inner join"):
    type = " " + type.upper() + " "
    out = """%s %s %s ON %s.%s = %s.%s """ % (table1, type, table2, table1, field1, table2, field2)
    return out

def query(table_name, fields = [], criteria = []):
    connection = _database_connection()
    try:
        with connection:
            cursor = connection.cursor()

            to_execute = _generate_query(table_name, fields, criteria)
            if to_execute is None:
                return None

            #print to_execute
            cursor.execute(to_execute)
            information = cursor.fetchall()
            return information
    except:
        traceback.print_exc(file=sys.stdout)