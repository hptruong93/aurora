# mySQL Database Functions
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Collection of methods for adding, updating, deleting, and querying the database
"""

import sys, json, os
import MySQLdb as mdb

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
        try:
            with self.con:
                cur = self.con.cursor()
                to_execute = "SELECT ap_slice_id FROM ap_slice WHERE tenant_id = \'" + \
                            str(tenant_id) + "\' AND project_id = \'" + \
                            str(project_id) + "\'"
                cur.execute(to_execute)
                tenant_ap_slices_tt = cur.fetchall()
                tenant_ap_slices = []
                for tenant_tuple in tenant_ap_slices_tt:
                    tenant_ap_slices.append(tenant_tuple[0])
                if ap_slice_id in tenant_ap_slices:
                    return True
                else:
                    return False
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
    
    #TODO: This function is untested
    def wnet_belongs_to(self, tenant_id, project_id, **kwargs):
        if 'wnet_id' in kwargs:
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT wnet_id FROM wnet WHERE tenant_id = \'" + \
                                str(tenant_id) + "\' AND project_id = \'" + \
                                str(project_id) + "\'")
                    tenants_wnets = cur.fetchall()
                    if wnet_id in tenant_wnets:
                        return True
                    else:
                        return False
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                sys.exit(1)
                        
        elif 'name' in kwargs:
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT name FROM wnet WHERE tenant_id = \'" + \
                                str(tenant_id) + "\' AND project_id = \'" + \
                                str(project_id) + "\'")
                    tenants_wnets = cur.fetchall()
                    if name in tenant_wnets:
                        return True
                    else:
                        return False
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                sys.exit(1)
        else:
            print "Error: expected keyword argument, specify wnet_id or name."

    def wslice_has_tag(self, ap_slice_id, tag):
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("SELECT name FROM tenant_tags WHERE ap_slice_id = \'" + \
                            str(ap_slice_id) + "\'")
                ap_slice_tags_tt = cur.fetchall()
                ap_slice_tags = []
                for tag_t in ap_slice_tags_tt:
                    ap_slice_tags.append(tag_t[0])
                if tag in ap_slice_tags:
                    return True
                else:
                    return False
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

    def wnet_add_wslice(self, tenant_id, slice_id, name):
        try:
            with self.con:
                #First get wnet-id
                cur = self.con.cursor()
                cur.execute("SELECT wnet_id FROM wnet WHERE wnet_id=\'" + \
                            str(name) + "\' OR name=\'" + str(name) + "\'")
                wnetID = cur.fetchone()[0]
                #Update to SQL database
                
                cur.execute("UPDATE ap_slice SET wnet_id=\'" + str(wnetID) + \
                            "\' WHERE ap_slice_id=\'" + str(slice_id)+"\'")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
           
    def wnet_remove_wslice(self, tenant_id, slice_id, name):        
        #Update to SQL database
        try:
            with self.con:
                #First get wnet-id
                cur = self.con.cursor()
                cur.execute("SELECT wnet_id FROM wnet WHERE wnet_id=\'" + \
                            str(name) + "\' OR name=\'" + str(name) + "\'")
                wnetID = cur.fetchone()[0]
                #Update to SQL database

                cur.execute("UPDATE ap_slice SET wnet_id=NULL WHERE ap_slice_id=\'"\
                            + str(slice_id) + "\' AND wnet_id=\'" + str(wnetID) + "\'")

        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
    def wnet_add(self, wnet_id, name, tenant_id, project_id):
        
        #Update the SQL database
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO wnet VALUES (%s, %s, %s, %s)",\
                            (str(wnet_id), str(name), str(tenant_id), str(project_id)))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def wnet_remove(self, identifier):
        #Update the SQL database, at this point we know the wnet exists under the specified tenant
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM wnet WHERE name=\'" + str(identifier) + \
                            "\' OR wnet_id=\'" + str(identifier) + "\'")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def slice_add(self, slice_uuid, tenant_id, physAP, project_id):
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO ap_slice VALUES (%s, %s, %s, %s, %s, %s)",\
                            ( str(slice_uuid), str(tenant_id),str(physAP),\
                              str(project_id), "NULL",        "PENDING") )
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def slice_delete(self, slice_id):
        #Update SQL database and JSON file
        pass
        
    def wslice_add_tag(self, ap_slice_id, tag):
        if self.wslice_has_tag(ap_slice_id, tag):
            return "Tag <%s> already exists for ap_slice <%s>\n" % (tag, ap_slice_id)
        else:
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("INSERT INTO tenant_tags VALUES (%s, %s)",\
                                ( tag, ap_slice_id ) )
                    return "Added tag <%s> to ap_slice <%s>.\n" % (tag, ap_slice_id)
            except mdb.Error, e:
                err_msg = "Error %d: %s\n" % (e.args[0], e.args[1])
                print err_msg
                return err_msg + '\n'
    
    def wslice_remove_tag(self, ap_slice_id, tag):
        if self.wslice_has_tag(ap_slice_id, tag):
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("DELETE FROM tenant_tags WHERE name=\'%s\' AND ap_slice_id=\'%s\'"
                                % (tag, ap_slice_id) )
                    return "Deleted tag <%s> from ap_slice <%s>\n" % (tag, ap_slice_id)
            except mdb.Error, e:
                err_msg = "Error %d: %s\n" % (e.args[0], e.args[1])
                print err_msg
                return err_msg + '\n'
        else:
            return "Tag <%s> not found.\n" % (tag)
            
         
    def wnet_join(self, tenant_id, name):
        pass #TODO AFTER SAVI INTEGRATION
      
      
        
        
        










