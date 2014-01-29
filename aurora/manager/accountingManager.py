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

    def update_status(self, unique_id, ap_up=True, ap_name=None):
        #Access Point is up update the ap_slice
        if ap_up:
            self.update_apslice(unique_id)
        #Access Point down fetch all ap_slice and update them
        else:
            try:
                with self.con:
                    cur = self.con.cursor()
                    if ap_name:
                        physical_ap = ap_name
                    else:
                        cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=%s", str(unique_id))
                        physical_ap = cur.fetchone()
                        if physical_ap:
                            physical_ap = physical_ap[0]
                        else:
                            raise Exception("Cannot fetch physical_ap for slice=%s\n" % unique_id)
                    #Get all slices associated with this ap
                    cur.execute("SELECT ap_slice_id FROM ap_slice WHERE physical_ap=%s", str(physical_ap))
                    raw_list = cur.fetchall()
                    if raw_list:
                        slice_list = []
                        for entry in raw_list:
                            slice_list.append(entry[0])
                    else:
                        raise Exception("No slices on physical_ap '%s'\n" % physical_ap)
                    for entry in slice_list:
                        self.update_apslice(entry)
            except Exception, e:
                print "Database Error: " + str(e)

    def update_apslice(self, unique_id):
        #TODO: Add checking so this doesn't execute for 
        #archived slices with "DELETED" status
        #print "update status"
        try:
            with self.con:
                cur = self.con.cursor()

                #Check ap slice status in ap_slice table
                cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=%s", str(unique_id))
                cur_status = cur.fetchone()[0]

                #Check ap slice status in ap_slice_status table
                row_count = cur.execute("SELECT * FROM ap_slice_status WHERE " \
                                        "ap_slice_id=%s", str(unique_id))
                if row_count > 0:
                    ap_slice_info = cur.fetchone()
                    pre_status = ap_slice_info[1]
                    time_active = ap_slice_info[2]
                    last_active_time = ap_slice_info[3]

                #Update ap_slice_status table
                if cur_status == 'ACTIVE':
                    if row_count == 0:
                        cur.execute("INSERT INTO ap_slice_status VALUES " \
                                    "(%s,%s,'0000',Now(),0)",
                                    (str(unique_id), 'ACTIVE'))
                    else:
                        cur.execute("UPDATE ap_slice_status SET "\
                                    "status='ACTIVE', last_active_time=Now() "\
                                    "WHERE ap_slice_id=%s", (str(unique_id)))
                else:
                    if row_count > 0 and pre_status == 'ACTIVE':
                        time_diff = datetime.datetime.now() - last_active_time
                        time_active = time_active + time_diff
                        cur.execute("UPDATE ap_slice_status SET status=%s, "\
                                    "time_active=%s WHERE ap_slice_id=%s",
                                    (cur_status, self.get_time_format(time_active), str(unique_id)))
                    else:
                        cur.execute("UPDATE ap_slice_status SET status=%s "\
                                    "WHERE ap_slice_id=%s", (cur_status, str(unique_id)))
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
