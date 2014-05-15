"""The sql_Info module is required to request the 
information and data storing in the SQL database.  
"""

from aurora import config
from aurora import query_agent as filter
import MySQLdb as mdb
import traceback
import sys

def _database_connection():
    return mdb.connect(config.CONFIG['mysql']['mysql_host'],
                               config.CONFIG['mysql']['mysql_username'],
                               config.CONFIG['mysql']['mysql_password'],
                               config.CONFIG['mysql']['mysql_db'])

def verify(ap_slice_ssid, tenant_id):
    result = filter.query('ap_slice', ['ap_slice_ssid'], ['ap_slice_ssid = "%s"' % ap_slice_ssid, \
                                                          'tenant_id = %s' % str(tenant_id), \
                                                          'status <> "DELETED"'])
    return len(result) == 0

def checkSliceNumber(args):
    link = _database_connection()
    try:
        with link:
            cursor = link.cursor()
            to_execute = """ SELECT name, (4 * number_radio - number_slice_free) 
                             AS occupied 
                             FROM ap 
                             WHERE name = "%s" """%(str(args))
            cursor.execute(to_execute)
            information = cursor.fetchall()
            return information
    except:
        traceback.print_exc(file=sys.stdout)
        
def checkAP_up(APname):
    link = _database_connection()
    try:
        with link:
            cursor = link.cursor()
            to_execute = """ select COUNT(*) from ap where name = "%s" 
                             AND status = "UP" """%(str(APname))
            cursor.execute(to_execute)
            information = cursor.fetchall()
            #print information[0][0]
            return information[0][0] != 0
    except:
        traceback.print_exc(file=sys.stdout)
        
def checkName(sliceName, tenantID):
    link = _database_connection()
    try:
        with link:
            cursor = link.cursor()
            to_execute = """ select COUNT(*) from ap_slice where ap_slice_ssid 
                            = "%s" and tenant_id = "%s" and status = 
                            "UP" """%(str(sliceName), str(tenantID))
            cursor.execute(to_execute)
            information = cursor.fetchall()
            print information[0][0]
            return information[0][0] == 0
            
            
            #to_execute = """ select COUNT(*) from ap_slice where ap_slice_ssid 
            #                = "%s" and tenant_id = "%s" and status = 
            #                "PENDING" """%(str(sliceName), str(tenantID))
            #cursor.execute(to_execute)
            #information = cursor.fetchall()
    except:
        traceback.print_exc(file=sys.stdout)


