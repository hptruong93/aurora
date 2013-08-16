# mySQL Database Startup Script
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
A Quick Script for creating the aurora database tables/schema
"""

import sys
import MySQLdb as mdb

class AuroraDBCreate():
    
    def __init__(self):
        #Connect to Aurora mySQL database
        try:
            self.con = mdb.connect(host='localhost', user='root', passwd='supersecret') #Change address
        
        except mdb.Error, e:
            
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
    
    def close(self):
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')
            
    def create_database(self):
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("CREATE DATABASE aurora")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
    
    def create_tables(self):
        try:
            with self.con:
                cur = self.con.cursor()
                #Switch to aurora database
                cur.execute("USE aurora")
                
                #Create access_point table
                access_point = "CREATE TABLE access_point (name VARCHAR(255) NOT NULL PRIMARY KEY,region VARCHAR(255),firmware VARCHAR(255),\
 version FLOAT,location VARCHAR(255),number_radio INT(11),memory_mb INT(11),free_disk INT(11),supported_protocol VARCHAR(255),\
 number_radio_free INT(11))"
                cur.execute(access_point)
                
                #Create ap_slice table
                ap_slice = "CREATE TABLE ap_slice (ap_slice_id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, tenant_id VARCHAR(255),\
 ap_slice_tags VARCHAR(255), physical_ap VARCHAR(255), firmware VARCHAR(255), project_id VARCHAR(255))"
                cur.execute(ap_slice)
                
                #Create wnet table
                wnet = "CREATE TABLE wnet( wnet_id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255) UNIQUE, management_network VARCHAR(255))"
                cur.execute(wnet)
                
                #Create wnet_ap_slice table
                wnet_ap_slice = "CREATE TABLE wnet_ap_slice(wnet_id INT(11) NOT NULL, ap_slice_id INT(11) NOT NULL, PRIMARY KEY(wnet_id, ap_slice_id))"
                cur.execute(wnet_ap_slice)
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
newDB = AuroraDBCreate()
newDB.create_database()
newDB.create_tables()
newDB.close()
