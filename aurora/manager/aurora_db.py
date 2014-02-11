# mySQL Database Functions
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Collection of methods for adding, updating, deleting, and querying the database
"""

import sys, json, os
import MySQLdb as mdb
import datetime

from pprint import pprint

class AuroraDB():
    #Default values in __init__ should potentially be omitted
    def __init__(self,
                 mysql_host = 'localhost',
                 mysql_username = 'root',
                 mysql_password = 'supersecret',
                 mysql_db = 'aurora'):
        print "Constructing AuroraDB..."
        #Connect to Aurora mySQL database
        try:
            self.con = mdb.connect(mysql_host, mysql_username,\
                                   mysql_password, mysql_db) #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

    def __del__(self):
        print "Destructing AuroraDB..."
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')

    def wslice_belongs_to(self, tenant_id, project_id, ap_slice_id):
        if tenant_id == 0:
            return True
        else:
            try:
                with self.con:
                    cur = self.con.cursor()
                    to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                                   "tenant_id = '%s' AND "
                                   "project_id = '%s'" % (tenant_id, project_id) )
                    cur.execute(to_execute)
                    tenant_ap_slices_tt = cur.fetchall()
                    tenant_ap_slices = []
                    for tenant_t in tenant_ap_slices_tt:
                        tenant_ap_slices.append(tenant_t[0])
                    if ap_slice_id in tenant_ap_slices:
                        return True

            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                sys.exit(1)
        return False

    def wnet_belongs_to(self, tenant_id, project_id, wnet_name):
        if tenant_id == 0:
            return True
        else:
            try:
                with self.con:
                    cur = self.con.cursor()
                    to_execute = ( "SELECT name, wnet_id FROM wnet WHERE "
                                   "tenant_id = '%s' AND "
                                   "project_id = '%s'" % (tenant_id, project_id) )
                    cur.execute(to_execute)
                    tenant_wnets_tt = cur.fetchall()

                    tenant_wnets = []
                    for t in tenant_wnets_tt:
                        tenant_wnets.append(t[0])
                        tenant_wnets.append(t[1])
                    if wnet_name in tenant_wnets:
                        return True
            except mdb.Error, e:
                    print "Error %d: %s" % (e.args[0], e.args[1])
                    sys.exit(1)
        return False

    def wslice_is_deleted(self, ap_slice_id):
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = ( "SELECT status FROM ap_slice WHERE "
                               "ap_slice_id = '%s'" % (ap_slice_id) )
                cur.execute(to_execute)
                status = cur.fetchone()
                if status[0] == 'DELETED':
                    return True
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        return False

    def wslice_has_tag(self, ap_slice_id, tag):
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = ( "SELECT name FROM tenant_tags WHERE "
                               "ap_slice_id = '%s'" % ap_slice_id )
                cur.execute(to_execute)
                ap_slice_tags_tt = cur.fetchall()
                ap_slice_tags = []
                for tag_t in ap_slice_tags_tt:
                    ap_slice_tags.append(tag_t[0])
                if tag in ap_slice_tags:
                    return True
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        return False

    def wnet_add_wslice(self, tenant_id, slice_id, name):
        try:
            with self.con:
                #First get wnet-id
                cur = self.con.cursor()
                #TODO: Catch tenant 0 call, ambiguous with multiple wnets of same name
                to_execute = ( "SELECT wnet_id FROM wnet WHERE "
                               "wnet_id='%s' AND tenant_id = '%s' OR "
                               "name='%s' AND tenant_id = '%s'" % (name, tenant_id, name, tenant_id) )
                cur.execute(to_execute)
                wnetID = cur.fetchone()[0]

                #TODO: Check if already exists
                to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                               "wnet_id = '%s'" % wnetID )
                cur.execute(to_execute)
                ap_slice_id_tt = cur.fetchall()
                ap_slice_id = []
                for id_t in ap_slice_id_tt:
                    ap_slice_id.append(id_t[0])
                if slice_id in ap_slice_id:
                    return "Slice '%s' already in '%s'.\n" % (slice_id, name)
                else:
                    #Update to SQL database
                    to_execute = ( "UPDATE ap_slice SET wnet_id='%s' WHERE "
                                   "ap_slice_id='%s'" % (wnetID, slice_id) )
                    cur.execute(to_execute)
                    return "Added '%s' to '%s'.\n" % (slice_id, name)

        except mdb.Error, e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            print err_msg
            return err_msg + '\n'

    def wnet_remove_wslice(self, tenant_id, slice_id, name):
        #Update to SQL database
        try:
            with self.con:
                #First get wnet-id
                cur = self.con.cursor()

                try:
                    wnet_info = self.get_wnet_name_id(name, tenant_id)
                except Exception as e:
                    raise Exception(e.message)

                wnet_id = wnet_info['wnet_id']
                wnet_name = wnet_info['name']


                #Update to SQL database
                to_execute = ( "UPDATE ap_slice SET wnet_id=NULL WHERE "
                               "ap_slice_id='%s' AND "
                               "wnet_id='%s' AND tenant_id = '%s'" % (slice_id, wnet_id, tenant_id) )
                cur.execute(to_execute)
                return "%s: %s removed\n" % (wnet_name, slice_id)
                #TODO: Add messaging
        except mdb.Error, e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            print err_msg
            return err_msg + '\n'

    def wnet_add(self, wnet_id, name, tenant_id, project_id):

        #Update the SQL database
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = ( "SELECT wnet_id FROM wnet WHERE "
                               "name = '%s' AND tenant_id = '%s'" % (name, tenant_id) )
                cur.execute(to_execute)
                wnet_id_tt = cur.fetchall()
                if len(wnet_id_tt) > 0:
                    return "You already own '%s'.\n" % name
                else:

                    to_execute = ( "INSERT INTO wnet VALUES ('%s', '%s', %s, %s)" %
                                   (wnet_id, name, tenant_id, project_id) )
                    cur.execute(to_execute)
                    return "Created '%s'.\n" % name
        except mdb.Error, e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            print err_msg
            return err_msg + '\n'

    def wnet_remove(self, wnet_arg, tenant_id):
        #Update the SQL database, at this point we know the wnet exists under the specified tenant
        #TODO: remove association from ap_slices
        try:
            with self.con:
                message = ""
                cur = self.con.cursor()
                try:
                    wnet_info = self.get_wnet_name_id(wnet_arg, tenant_id)
                except Exception as e:
                    raise Exception(e.message)
                wnet_id = wnet_info['wnet_id']
                wnet_name = wnet_info['name']

                if tenant_id == 0:
                    to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                                   "wnet_id = '%s'" % wnet_id )
           #         to_execute_slice = ( "UPDATE ap_slice SET wnet_id = NULL WHERE "
           #                              "wnet_id = '%s'" % wnet_id )
                    to_execute_wnet = ( "DELETE FROM wnet WHERE wnet_id = '%s'" % wnet_id )
                else:
                    to_execute = ( "SELECT ap_slice_id FROM ap_slice WHERE "
                                   "wnet_id = '%s' AND tenant_id = '%s'" %
                                   (wnet_id, tenant_id) )
           #         to_execute_slice = ( "UPDATE ap_slice SET wnet_id = NULL WHERE "
           #                            "wnet_id = '%s' AND tenant_id = '%s'" %
           #                            (wnet_id, tenant_id) )
                    to_execute_wnet = ( "DELETE FROM wnet WHERE wnet_id = '%s'"
                                        "AND tenant_id = '%s'" % (wnet_id, tenant_id) )
                cur.execute(to_execute)
                slice_id_tt = cur.fetchall()
                if slice_id_tt:
             #       message += "\nRemoving slices from '%s':" % wnet_arg
                    for slice_id_t in slice_id_tt:
                        message += self.wnet_remove_wslice(tenant_id, slice_id_t[0], wnet_id)
                    message += '\n'
           #     cur.execute(to_execute_slice)
                message += "Deleting '%s'.\n" % wnet_arg
                cur.execute(to_execute_wnet)

        except mdb.Error, e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            print err_msg
            return err_msg + '\n'
        return message

    def wslice_add(self, slice_uuid, slice_ssid, tenant_id, physAP, project_id):
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = ( "INSERT INTO ap_slice VALUES ('%s', '%s', %s, '%s', %s, %s, '%s')" %
                               (slice_uuid, slice_ssid, tenant_id, physAP,
                                project_id, "NULL", "PENDING") )
                cur.execute(to_execute)
                #return "Adding slice %s on %s.\n" % (slice_uuid, physAP)
                return None
                #We the manager calling this method will generate this message after calling.
                #Therefore it is not necessary to return a success notification. The message
                #can be used for testing purposes.
                #Return None when there is no problem instead.
        except mdb.Error, e:
            err_msg = "-->> Error %d: %s" % (e.args[0], e.args[1])
            print err_msg
            return err_msg + '\n'

    def wslice_delete(self, slice_id):
        #Update SQL database and JSON file
        #Remove tags
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = ( "UPDATE ap_slice SET status='DELETING' WHERE "
                               "ap_slice_id='%s'" % slice_id )
                cur.execute(to_execute)
                to_execute = ( "DELETE FROM tenant_tags WHERE "
                               "ap_slice_id='%s'" % slice_id )
                cur.execute(to_execute)
                return "Deleting slice %s.\n" % slice_id
        except mdb.Error, e:
            err_msg = "Error %d: %s" % (e.args[0], e.args[1])
            print err_msg
            return err_msg + '\n'

    def wslice_add_tag(self, ap_slice_id, tag):
        if self.wslice_has_tag(ap_slice_id, tag):
            return "Tag '%s' already exists for ap_slice '%s'\n" % (tag, ap_slice_id)
        else:
            try:
                with self.con:
                    cur = self.con.cursor()
                    to_execute = "INSERT INTO tenant_tags VALUES (%s, '%s')" % (tag, ap_slice_id)
                    cur.execute(to_execute)
                    return "Added tag '%s' to ap_slice '%s'.\n" % (tag, ap_slice_id)
            except mdb.Error, e:
                err_msg = "Error %d: %s\n" % (e.args[0], e.args[1])
                print err_msg
                return err_msg + '\n'

    def wslice_remove_tag(self, ap_slice_id, tag):
        if self.wslice_has_tag(ap_slice_id, tag):
            try:
                with self.con:
                    cur = self.con.cursor()
                    to_execute = ( "DELETE FROM tenant_tags WHERE "
                                   "name='%s' AND ap_slice_id='%s'" %
                                   (tag, ap_slice_id) )
                    cur.execute(to_execute)
                    return "Deleted tag '%s' from ap_slice '%s'\n" % (tag, ap_slice_id)
            except mdb.Error, e:
                err_msg = "Error %d: %s\n" % (e.args[0], e.args[1])
                print err_msg
                return err_msg + '\n'
        else:
            return "Tag '%s' not found.\n" % (tag)

    def wnet_join(self, tenant_id, name):
        pass #TODO AFTER SAVI INTEGRATION

    def get_wslice_physical_ap(self, ap_slice_id):
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = ( "SELECT physical_ap FROM ap_slice WHERE "
                               "ap_slice_id='%s'" % ap_slice_id )
                cur.execute(to_execute)
                physical_ap = cur.fetchone()
                if physical_ap:
                    return physical_ap[0]
                else:
                    raise Exception("No slice '%s'\n" % ap_slice_id)
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

    def get_wslice_status(self, ap_slice_id):
        #get ap slice active time and bytes_sent
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("SELECT * FROM ap_slice_status WHERE \
                            ap_slice_id = '%s'" % ap_slice_id)
                ap_info = cur.fetchone()
                if ap_info:
                    status = ap_info[1]
                    time_active = ap_info[2]
                    last_active_time = ap_info[3]
                    bytes_sent = ap_info[4]
                    if status == 'ACTIVE':
                        time_active += datetime.datetime.now() - last_active_time
                    return (time_active, bytes_sent)
                else:
                    raise Exception("No slice '%s'\n" % ap_slice_id)
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

    def get_wnet_list(self, tenant_id, wnet_arg = None):
        try:
            with self.con:
                cur = self.con.cursor()
                if tenant_id == 0:
                    to_execute = "SELECT * FROM wnet"
                elif wnet_arg:
                    to_execute = ( "SELECT * FROM wnet WHERE "
                                   "tenant_id = '%s' AND wnet_id = '%s' OR "
                                   "tenant_id = '%s' AND name = '%s'" %
                                   (tenant_id, wnet_arg, tenant_id, wnet_arg) )
                else:
                    to_execute = "SELECT * FROM wnet WHERE tenant_id = '%s'" % tenant_id
                cur.execute(to_execute)
                wnet_tt = cur.fetchall()
                if not wnet_tt:
                    err_msg = "AuroraDB Error: No wnets available"
                    if wnet_arg:
                        err_msg += " by handle '%s'" % wnet_arg
                    err_msg += ".\n"
                    raise Exception(err_msg)
                #Prune through list
                wnet_list = []
                for (i, wnet_t) in enumerate(wnet_tt):
                    wnet_list.append({})
                    wnet_list[i]['wnet_id'] = wnet_t[0]
                    wnet_list[i]['name'] = wnet_t[1]
                    wnet_list[i]['tenant_id'] = wnet_t[2]
                    wnet_list[i]['project_id'] = wnet_t[3]
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        return wnet_list

    def get_wnet_slices(self, wnet_arg, tenant_id):
        try:
            with self.con:
                cur = self.con.cursor()
                wnet_id = self.get_wnet_name_id(wnet_arg, tenant_id)['wnet_id']

                #Get slices associated with this wnet
                cur.execute( "SELECT * FROM ap_slice WHERE "
                             "wnet_id = '%s'" % wnet_id )
                slice_info_tt = cur.fetchall()

                #Prune through list
                slice_list = []
                for (i, slice_t) in enumerate(slice_info_tt):
                    slice_list.append({})
                    slice_list[i]['ap_slice_id'] = slice_t[0]
                    slice_list[i]['ap_slice_ssid'] = slice_t[1]
                    slice_list[i]['tenant_id'] = slice_t[2]
                    slice_list[i]['physical_ap'] = slice_t[3]
                    slice_list[i]['project_id'] = slice_t[4]
                    slice_list[i]['wnet_id'] = slice_t[5]
                    slice_list[i]['status'] = slice_t[6]
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        return slice_list

    def get_wnet_name_id(self, wnet_arg, tenant_id):
        try:
            with self.con:
                cur = self.con.cursor()
                wnet_info = {}
                if tenant_id == 0:
                    to_execute = ( "SELECT wnet_id, name FROM wnet WHERE "
                                   "name='%s' OR wnet_id = '%s'" % (wnet_arg, wnet_arg) )
                else:
                    to_execute = ( "SELECT wnet_id, name FROM wnet WHERE "
                                   "name='%s' AND tenant_id = '%s' OR "
                                   "wnet_id='%s' AND tenant_id = '%s'" %
                                   (wnet_arg, tenant_id, wnet_arg, tenant_id) )
                cur.execute(to_execute)
                wnet_info_tt = cur.fetchall()
                if not wnet_info_tt:
                    raise Exception("AuroraDB Error: No wnet '%s'.\n" % wnet_arg)
                elif tenant_id == 0 and len(wnet_info_tt) > 1:
                    err_msg = "Ambiguous input.  Did you mean:"
                    for wnet_info_t in wnet_info_tt:
                        err_msg += "\n\t%s: %s - %s" % (wnet_arg, wnet_info_t[0], wnet_info-t[1])
                    raise Exception(err_msg)
                else:
                    wnet_info['wnet_id'] = wnet_info_tt[0][0]
                    wnet_info['name'] = wnet_info_tt[0][1]

        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        return wnet_info