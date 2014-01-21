#
#SAVI Group: Feier Chen


import datetime
import MySQLdb as mdb
import atexit
import sys


class accountingManager():

    def __init__(self, host, username, password):

        #Connect to Aurora mySQL Database
        print "Connecting to SQLdb in accountingManager...."
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

        atexit.register(self.closeSQL)

    def closeSQL(self):
        print "Closing SQL connectiong in accountingManager..."
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')

    def update_status(self, unique_id):
        print "update status"
        try:
            with self.con:
                cur = self.con.cursor()

                #Check ap slice status in ap_slice table
                cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=%s",
                            str(unique_id))
                cur_status = cur.fetchone()[0]

                #Check ap slice status in ap_slice_status table
                row_count = cur.execute("SELECT * FROM ap_slice_status WHERE \
                                        ap_slice_id=%s", str(unique_id))
                if row_count > 0:
                    ap_slice_info = cur.fetchone()
                    pre_status = ap_slice_info[1]
                    time_active = ap_slice_info[2]
                    last_active_time = ap_slice_info[3]

                #Update ap_slice_status table
                if cur_status == 'ACTIVE':
                    if row_count == 0:
                        cur.execute("INSERT INTO ap_slice_status VALUES\
                                    (%s,%s,'0000',Now(),0)",
                                    (str(unique_id), 'ACTIVE'))
                    else:
                        cur.execute("UPDATE ap_slice_status SET \
                                    status='ACTIVE', last_active_time=Now()\
                                    WHERE ap_slice_id=%s", (str(unique_id)))
                else:
                    if row_count > 0 and pre_status == 'ACTIVE':
                        time_diff = datetime.datetime.now() - last_active_time
                        time_active = time_active + time_diff
                        cur.execute("UPDATE ap_slice_status SET status=%s,\
                                    time_active=%s WHERE ap_slice_id=%s",
                                    (cur_status, self.get_time_format(time_active), str(unique_id)))
                    else:
                        cur.execute("UPDATE ap_slice_status SET status=%s,\
                                    WHERE ap_slice_id=%s", (cur_status, str(unique_id)))
        except Exception, e:
            print "Database Error: " + str(e)

    def get_time_format(self, time):
        time = time.total_seconds()
        hours = int(time // 3600)
        time = time - hours * 3600
        miniutes = int(time // 60)
        time = time - miniutes * 60
        seconds = int(time)
        time_format = str(hours) + ':' + str(miniutes) + ':' + str(seconds)
        return time_format
