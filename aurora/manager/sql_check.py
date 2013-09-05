# SQL Database Consistency Check
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, sys, os
import MySQLdb as mdb

class SQLCheck():
    
    def __init__(self):
        try:
            JFILEAP = open('json/aplist.json', 'r')
            JFILEWNET = open('json/wnet.json', 'r')
            self.AP = json.load(JFILEAP)
            self.wnet = json.load(JFILEWNET)
            JFILEAP.close()
            JFILEWNET.close()
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        self.apslice_list = []
        #Determine number of tenant ids/apslice json files
        filenames = os.listdir('json')
        #Get all files with prefix 'apslice-'
        filenames = filter(lambda x: 'apslice-' in x, filenames)
        #Get rid of all temp files
        filenames = filter(lambda x: '~' != x[len(x)-1], filenames)
       
        #Load each file into apslice_list
        for entry in filenames:
            try:
                JFILE = open('json/'+entry, 'r')
                self.apslice_list.append(json.load(JFILE))
                JFILE.close()
            except IOError:
                print('Error opening file!')
                sys.exit(-1)
          
        #Connect to Aurora mySQL Database
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
            
    def closeSQL(self):
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')
    
    def syncAll(self):
        print('Synchronizing JSON database with SQL database...')
        self.syncAP()
        self.syncAPSlice()
        self.syncWnet()
        self.closeSQL()
        
    def syncAP(self):
        print('Now synchronizing Access Points...')
        #First clear the table
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM access_point")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
        #Loop through all entries and add into table    
        for entry in self.AP:
            pstatement = (entry[0], entry[1]['region'], entry[1]['firmware'], entry[1]['version'], entry[1]['location'], entry[1]['number_radio'], 
                          entry[1]['memory_mb'], entry[1]['free_disk'], entry[1]['supported_protocol'], entry[1]['number_radio_free'])
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("INSERT INTO access_point VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", pstatement)
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        
    def syncAPSlice(self):
        print('Now synchronizing AP Slices...')
        #First clear the table
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM ap_slice")
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
        
        #Loop through all entries and add into table
        for tenant in self.apslice_list:
            for entry in tenant:
                pstatement = (str(entry['ap_slice_id']), str(entry['tenant_id']), entry['ap_slice_tags'], entry['physical_ap'], entry['firmware'],
                              str(entry['project_id']), str(entry['wnet_id']))
                try:
                    with self.con:
                        cur = self.con.cursor()
                        cur.execute("INSERT INTO ap_slice VALUES (%s, %s, %s, %s, %s, %s, %s)", pstatement)
                except mdb.Error, e:
                    print "Error %d: %s" % (e.args[0], e.args[1])
                    
    def syncWnet(self):
        print('Now synchronizing Wnet...')
        #First clear the table
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM wnet")
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
        #Loop through all entries and add into table
        for entry in self.wnet:
            pstatement = (entry['wnet_id'], entry['name'], entry['tenant_id'])
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("INSERT INTO wnet VALUES (%s, %s, %s)", pstatement)
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        
SQLCheck().syncAll()
