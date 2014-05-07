"""The sql_Info module is required to request the 
information and data storing in the SQL database.  
"""

import MySQLdb as mdb
import config

def _database_connection():
    return mdb.connect(config.CONFIG['mysql']['mysql_host'],
                               config.CONFIG['mysql']['mysql_username'],
                               config.CONFIG['mysql']['mysql_password'],
                               config.CONFIG['mysql']['mysql_db'])

def verify(args):
    link = _database_connection()
    try:
        with link:
            cursor = link.cursor()
            to_execute = """ select COUNT(distinct ap_slice_ssid) from ap_slice where status <> "DELETED" and ap_slice_ssid = "%s" """%(str(args))
            cursor.execute(to_execute)
            information = cursor.fetchall()
    except:
        print "There is an error in verify from sql_Info.py!!!"
    if information[0][0] == 0:
        return "true"

def checkSliceNumber(args):
    link = _database_connection()
    try:
        with link:
            cursor = link.cursor()
            to_execute = """ select name, (4 * number_radio - number_slice_free) as occupied from ap where name = "%S" """%(str(args))
            cursor.execute(to_execute)
            information = cursor.fetchall()
    except:
        print "There is an error in checkSliceNumber from sql_Info.py!!!"


