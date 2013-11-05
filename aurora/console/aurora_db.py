# mySQL Database Functions
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Collection of methods for adding, updating, deleting, and querying the database
"""

import sys, json
import MySQLdb as mdb

class AuroraDB():

    def __init__(self):
        #Connect to Aurora mySQL database
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        
        except mdb.Error, e:
            
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
    
    def close(self):
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')
    
    def addAP(self, name, region, firmware, version, location, numradio, memory, freedisk, proto):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO access_point VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (name, region, firmware, str(version), location, str(numradio), str(memory), str(freedisk), proto))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def updateAP(self, oldname, name, region, firmware, version, location, numradio, memory, freedisk, proto):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("UPDATE access_point SET name=%s, region=%s, firmware=%s, version=%s, location=%s, number_radio=%s, \
                    memory_mb=%s, free_disk=%s, supported_protocol=%s WHERE name=%s",
                    (name, region, firmware, str(version), location, str(numradio), str(memory), str(freedisk), proto, oldname))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def deleteAP(self, name):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM access_point WHERE name=%s", (name))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def addAPSlice(self, tenid, tags, physicalap, firmware, pid):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO ap_slice VALUES (DEFAULT, %s, %s, %s, %s, %s)", (tenid, tags, physicalap, firmware, pid))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def updateAPSlice(self, id, tenid, tags, physicalap, firmware, pid):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("UPDATE ap_slice SET tenant_id=%s, ap_slice_tags=%s, physical_ap=%s, firmware=%s, project_id=%s WHERE ap_slice_id=%s",
                    (tenid, tags, physicalap, firmware, pid, id))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def deleteAPSlice(self, id):
    
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM ap_slice WHERE ap_slice_id="+str(id))
                
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def addWnet(self, name, man_network):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO wnet VALUES (DEFAULT, %s, %s)", (name, man_network))
                
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def updateWnet(self, id, name, man_network):
        #id = id of entry to update, name and man_network are update values
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("UPDATE wnet SET name='"+name+"', management_network='"+man_network+"' WHERE wnet_id='"+str(id)+"'")
                
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def deleteWnet(self, id):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM wnet WHERE wnet_id='"+str(id)+"'")
                
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def queryWnetSlices(self, wnet_id):
    #Return all slices belonging to a wnet (id)
        try:
            with self.con:
                cur = self.con.cursor(mdb.cursors.DictCursor)
                cur.execute("SELECT A.ap_slice_id, tenant_id, ap_slice_tags, physical_ap, firmware, project_id FROM wnet_ap_slice W JOIN \
                    ap_slice A ON W.ap_slice_id=A.ap_slice_id WHERE W.wnet_id='"+str(wnet_id)+"'")
                result = cur.fetchall()
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
        
        return result
    
    def addEntry(self, table, values):
        #Values is a tuple containing the entry (each entry in the tuple should be a string
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO "+table+" VALUES "+str(values))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def updateEntry(self, table, keyColumn, keyValue, updateColumn, updateValue):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("UPDATE "+table+" SET "+updateColumn+"='"+str(updateValue)+"' WHERE "+keyColumn+"='"+str(keyValue)+"'")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def deleteEntry(self, table, column, value):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM "+table+" WHERE "+column+"='"+str(value)+"'")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def addWnetAPSlice(self, wnet_id, ap_slice_id):
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO wnet_ap_slice VALUES (%s, %s)", (str(wnet_id), str(ap_slice_id)))
                
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
    def deleteWnetAPSlice(self, wnet_id, ap_slice_id):
        
        try:
            with self.con:
                cur= self.con.cursor()
                cur.execute("DELETE FROM wnet_ap_slice WHERE wnet_id='"+str(wnet_id)+"' AND ap_slice_id='"+str(ap_slice_id)+"'")
                
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def queryTable(self, table, column , value):
    
        try:
            with self.con:
                cur = self.con.cursor(mdb.cursors.DictCursor)
                cur.execute("SELECT * FROM "+table+" WHERE "+column+"='"+str(value)+"'")
                result = cur.fetchall()
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
        
        return result
    
    def fetchall(self, tname):
        
        try:
            with self.con:
                cur = self.con.cursor(mdb.cursors.DictCursor)
                cur.execute("SELECT * FROM "+tname)
                result = cur.fetchall()
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])        
        
        return result
        
#testDB = AuroraDB()
#print testDB.queryWnetSlices(3)
#testDB.close() 
