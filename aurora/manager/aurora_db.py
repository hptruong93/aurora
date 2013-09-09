# mySQL Database Functions
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Collection of methods for adding, updating, deleting, and querying the database
"""

import sys, json, os
import MySQLdb as mdb

class AuroraDB():

    def __init__(self):
        #Connect to Aurora mySQL database
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        #Load JSON Files
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
        #Sort alphabetically
        filenames = sorted(filenames)
       
        #Load each file into apslice_list
        for entry in filenames:
            try:
                JFILE = open('json/'+entry, 'r')
                self.apslice_list.append(json.load(JFILE))
                JFILE.close()
            except IOError:
                print('Error opening file!')
                sys.exit(-1)
    
    def __del__(self):
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')
    
    def wnet_add_slice(self, tenant_id, slice_id, name):
        #Get the wnet_id
        wnet_id = -1
        for entry in self.wnet:
            if str(entry['name']) == name:
                wnet_id = entry['wnet_id']
        
        if wnet_id == -1:
            print('wnet_id not found!')
            return
        
        #Change the wnet JSON file
        for wnet in self.wnet:
            if int(wnet['wnet_id']) == wnet_id:
                if slice_id not in wnet['ap-slices']:
                    wnet['ap-slices'].append(slice_id)
                else:
                    print('This wnet already contains the specified slice!')
                    return
        try:
            JFILE = open('json/wnet.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        json.dump(self.wnet, JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()
        
        #Change the apslice JSON file
        for entry in self.apslice_list[tenant_id-1]:
            if int(entry['ap_slice_id']) == slice_id:
                entry['wnet_id'] = wnet_id
        try:
            JFILE = open('json/apslice-'+str(tenant_id)+'.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        json.dump(self.apslice_list[tenant_id-1], JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()
        
        #Update to SQL database
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("UPDATE ap_slice SET wnet_id="+str(wnet_id)+" WHERE ap_slice_id="+str(slice_id))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
           
    def wnet_remove_slice(self, tenant_id, slice_id, name):
        #Get the wnet_id
        wnet_id = -1
        for entry in self.wnet:
            if str(entry['name']) == name:
                wnet_id = entry['wnet_id']
        
        if wnet_id == -1:
            print('wnet_id not found!')
            return
    
        #Change the wnet JSON file
        for wnet in self.wnet:
            if int(wnet['wnet_id']) == wnet_id:
                if slice_id in wnet['ap-slices']:
                    wnet['ap-slices'].remove(slice_id)
                else:
                    print('This wnet does not contain the specified slice!')
                    return
        try:
            JFILE = open('json/wnet.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        json.dump(self.wnet, JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()
        
        #Change the apslice JSON file
        for entry in self.apslice_list[tenant_id-1]:
            if int(entry['ap_slice_id']) == slice_id:
                if int(entry['wnet_id']) == wnet_id:
                    entry['wnet_id'] = None
                else:
                    print('Error. Slice not associated with specified wnet_id!')
                    return
        try:
            JFILE = open('json/apslice-'+str(tenant_id)+'.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        json.dump(self.apslice_list[tenant_id-1], JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()
        
        #At this point, we know that both json file removals have succeeded (i.e. we don't need to check
        #the database for wnet_id, we can just set it to NULL)
        #Update to SQL database
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("UPDATE ap_slice SET wnet_id=NULL WHERE ap_slice_id="+str(slice_id))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
    def wnet_add(self, tenant_id, name, slices,agg_rate, qos, shareable):
        #First we need to generate a new wnet_id
        id_list = []
        for entry in self.wnet:
            id_list.append(entry['wnet_id'])
        new_id = max(id_list) + 1
        
        #Change the wnet JSON file
        data = {}
        data['name'] = name
        data['wnet_id'] = new_id
        data['ap-slices'] = slices
        data['tenant_id'] = tenant_id
        data['qos_priority'] = qos
        data['is_shareable'] = shareable
        data['aggregate_rate'] = agg_rate
        self.wnet.append(data)
        try:
            JFILE = open('json/wnet.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        json.dump(self.wnet, JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()
    
        #Update the SQL database
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("INSERT INTO wnet VALUES (%s, %s, %s)", (str(new_id), name, str(tenant_id)))
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def wnet_remove(self, tenant_id, name):
        found = False
        #Change the wnet JSON file
        for (index,entry) in enumerate(self.wnet):
            if str(entry['name']) == name and int(entry['tenant_id']) == tenant_id:
                found = True
                self.wnet.pop(index)
        
        if not found:
            print('Specified wnet not found!')
            return
        
        try:
            JFILE = open('json/wnet.json', 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        json.dump(self.wnet, JFILE, sort_keys=True, indent=4)
        JFILE.flush()
        JFILE.close()
        
        #Update the SQL database, at this point we know the wnet exists under the specified tenant
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("DELETE FROM wnet WHERE name='"+str(name)+"'")
        
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            
    def wnet_join(self, tenant_id, name):
        pass #TODO AFTER SAVI INTEGRATION
        
