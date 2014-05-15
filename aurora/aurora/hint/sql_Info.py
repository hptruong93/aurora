# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

"""The sql_Info module is required to request the 
information and data storing in the SQL database.  
"""

from aurora import config
from aurora import query_agent as filter
import traceback
import sys

def verify(ap_slice_ssid, tenant_id):
    result = filter.query('ap_slice', ['ap_slice_ssid'], ['ap_slice_ssid = "%s"' % ap_slice_ssid, \
                                                          'tenant_id = %s' % str(tenant_id), \
                                                          'status <> "DELETED"'])
    return len(result) == 0

def checkSliceNumber(args):
    return filter.query('ap', ['name', '(4 * number_radio - number_slice_free) AS occupied'], ['name = "%s"' % str(args)])