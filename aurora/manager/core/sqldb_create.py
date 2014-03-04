# mySQL Database Startup Script
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
A Quick Script for creating the aurora database tables/schema
"""
import logging
import sys
import traceback

import MySQLdb as mdb

LOGGER = logging.getLogger(__name__)

class SQLDBCreate(object):

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
                LOGGER.warn("Creating database")
                cur.execute("DROP DATABASE IF EXISTS aurora")
                cur.execute("CREATE DATABASE aurora")

        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def create_tables(self):
        try:
            with self.con:
                cur = self.con.cursor()
                #Switch to aurora database
                cur.execute("USE aurora")

                #Create ap table
                LOGGER.warn("Creating table ap")
                ap = "CREATE TABLE ap (name VARCHAR(255) NOT NULL PRIMARY KEY,region VARCHAR(255),firmware VARCHAR(255),\
 version VARCHAR(255),number_radio INT(11),memory_mb INT(11),free_disk INT(11),supported_protocol VARCHAR(255) DEFAULT 'a/b/g',\
 number_radio_free INT(11), number_slice_free INT(11), status ENUM('UP','DOWN','UNKNOWN'))"
                cur.execute(ap)

                #Create ap_slice table
                LOGGER.warn("Creating table ap_slice")
                ap_slice = "CREATE TABLE ap_slice (ap_slice_id VARCHAR(40) NOT NULL PRIMARY KEY, ap_slice_ssid VARCHAR(255), tenant_id VARCHAR(255),\
 physical_ap VARCHAR(255), project_id VARCHAR(255), wnet_id VARCHAR(40), status ENUM('PENDING','ACTIVE','FAILED','DOWN','DELETING','DELETED'))"
                cur.execute(ap_slice)

                #Create metering table
                LOGGER.warn("Creating table metering")
                metering = """CREATE TABLE metering(
                                  ap_slice_id VARCHAR(40) NOT NULL PRIMARY KEY, 
                                  current_mb_sent FLOAT DEFAULT 0.0, 
                                  total_mb_sent FLOAT DEFAULT 0.0,
                                  current_active_duration TIME DEFAULT '00:00:00',
                                  total_active_duration TIME DEFAULT '00:00:00',
                                  last_time_activated DATETIME,
                                  last_time_updated DATETIME
                                  )
                                  """
                cur.execute(metering)

                #Create wnet table
                LOGGER.warn("Creating table wnet")
                wnet = "CREATE TABLE wnet (wnet_id VARCHAR(40) NOT NULL PRIMARY KEY, name VARCHAR(255) UNIQUE, tenant_id VARCHAR(255), project_id VARCHAR(40))"
                cur.execute(wnet)

                #Create location_tags table
                LOGGER.warn("Creating table location_tags")
                location_tags = "CREATE TABLE location_tags (name VARCHAR(255), ap_name VARCHAR(255), PRIMARY KEY(name, ap_name))"
                cur.execute(location_tags)

                #Create tenant_tags table
                LOGGER.warn("Creating table tenant_tags")
                tenant_tags = "CREATE TABLE tenant_tags (name VARCHAR(255), ap_slice_id VARCHAR(40), PRIMARY KEY(name, ap_slice_id))"
                cur.execute(tenant_tags)

        except mdb.Error, e:
            traceback.print_exc(file=sys.stdout)

logging.basicConfig()
newDB = SQLDBCreate()
newDB.create_database()
newDB.create_tables()
newDB.close()
