# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

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

def _build_query(table_name, fields, criteria):
    if len(fields) == 0:
        to_execute = """SELECT * FROM (%s)""" % table_name
    else:
        to_execute = "SELECT " + ",".join(fields) + " FROM (%s)" % table_name

    #Now parse the criteria
    if len(criteria) != 0:
        to_execute += " WHERE "
        to_execute += " AND ".join(criteria)
    return to_execute + appendix

def join_criteria(criteria_list, joiner = 'AND'):
    joiner = " %s " % joiner
    output = joiner.join(criteria_list)
    return  "(%s)" % output

def join_table(table1, table2, field1, field2, type = "inner join"):
    type = " " + type.upper() + " "
    out = """%s %s %s ON %s.%s = %s.%s """ % (table1, type, table2, table1, field1, table2, field2)
    return out

def join_criteria(criteria_list, criteria_joiner):
    joiner = " %s " % criteria_joiner
    return joiner.join(map(lambda x : "(%s)" % x, criteria_list))

def query(table_name, fields = [], criteria = [], appendix = ''):
    """Interface to query the mysql database.

        :param str table_name: name of the table to query
        :param list fields: selected fields of the table that will be queried. This is a list os strings
        :param list criteria: criteria used for filtering (e.g. fields1 > 3). This is a list of strings

        :rtype: tuple
    """
    connection = _database_connection()
    try:
        with connection:
            cursor = connection.cursor()

            to_execute = _build_query(table_name, fields, criteria)
            if to_execute is None:
                return None

            print to_execute
            cursor.execute(to_execute)
            information = cursor.fetchall()
            return information
    except:
        traceback.print_exc(file=sys.stdout)
