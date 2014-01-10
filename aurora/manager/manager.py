# Aurora Manager Functions
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json
import sys, uuid
from slice_plugin import *
from aurora_db import *
import MySQLdb as mdb
import dispatcher
import provision_server.ap_provision as provision

import time

from pprint import pprint

class Manager():
    
    def __init__(self):
        
        print("Constructing Manager")

        ### Dispatcher variables
        host = 'localhost'
        username = 'outside_world'
        password = 'wireless_access'
        mysql_host = host
        mysql_username = 'root'
        mysql_password = 'supersecret'
        mysql_db = 'aurora'
        
        #Initialize AuroraDB Object
        self.auroraDB = AuroraDB(mysql_host, mysql_username, mysql_password, mysql_db)
    ##Commented for testing without AP 
        self.dispatch = dispatcher.Dispatcher(host, username, password, mysql_username, mysql_password)
        provision.run()
        
 #       print "Sleeping for 10"
 #       time.sleep(10)
        
    def __del__(self):
    #   self.dispatch.stop()
        print("Destructing Manager...")
        self.dispatch.stop()
        provision.stop()
        
    def parseargs(self, function, args, tenant_id, user_id, project_id):
        # args is a generic dictionary passed to all functions (each function is responsible for parsing
        # their own arguments
        function = function.replace('-', '_') #For functions in python
        response = getattr(self, function)(args, tenant_id, user_id, project_id)
        return response
    
    def ap_filter(self, args): #STILL NEED TO IMPLEMENT TAG SEARCHING (location_tags table), maybe another connection with intersection?
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        if len(args) == 0: #No filter or tags
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT * FROM ap")
                    tempList =  cur.fetchall()
                    #Prune thorugh list
                    newList = []
                    for i in range(len(tempList)):
                        newList.append([])
                        newList[i].append(tempList[i][0])
                        newList[i].append({})
                        newList[i][1]['region'] = tempList[i][1]
                        newList[i][1]['firmware'] = tempList[i][2]
                        newList[i][1]['version'] = tempList[i][3]
                        newList[i][1]['number_radio'] = tempList[i][4]
                        newList[i][1]['memory_mb'] = tempList[i][5]
                        newList[i][1]['free_disk'] = tempList[i][6]
                        newList[i][1]['supported_protocol'] = tempList[i][7]
                        newList[i][1]['number_radio_free'] = tempList[i][8]
                        #Get a list of tag
                        cur.execute("SELECT name FROM location_tags WHERE ap_name=\'"+str(tempList[i][0])+"\'")
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i][1]['tags'] = tagString
                    return newList
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        else: #Multiple arguments (name=openflow & firmware=openwrt & region=mcgill & number_radio>1)
            tag_compare = False #For tags, we need 2 queries and a quick result compare at the end
            tag_result = []
            args_list = args.split('&')
            for (index, entry) in enumerate(args_list):
                args_list[index] = entry.strip()
                 #Filter for tags (NOT Query is not yet implemented (future work?), support for only 1 tag (USE 'OR' STATEMENT IN FUTURE FOR MULTIPLE))
                if 'tag' in args_list[index]:
                    tag_compare = True
                    try:
                        with self.con:
                            cur = self.con.cursor()
                            if '=' in args_list[index]:
                                cur.execute("SELECT ap_name FROM location_tags WHERE name=\'"+args_list[index].split('=')[1]+"\'")
                            else:
                                print("Unexpected character in tag query. Please check syntax and try again!")
                                sys.exit(0)
                            tempresult = cur.fetchall()
                            for result in tempresult:
                                tag_result.append(result[0])
                                
                    except mdb.Error, e:
                        print "Error %d: %s" % (e.args[0], e.args[1])
                        
                elif '=' in args_list[index]:
                    if (args_list[index].split('=')[0] == "name") or (args_list[index].split('=')[0] == "firmware") or (args_list[index].split('=')[0] == "region") or (args_list[index].split('=')[0] == "supported_protocol"):
                        args_list[index] = args_list[index].split('=')[0]+'=\''+args_list[index].split('=')[1]+'\''
                elif '!' in args_list[index]:
                    if (args_list[index].split('!')[0] == "name") or (args_list[index].split('!')[0] == "firmware") or (args_list[index].split('!')[0] == "region") or (args_list[index].split('!')[0] == "supported_protocol"):
                        args_list[index] = args_list[index].split('!')[0]+'<>\''+args_list[index].split('!')[1]+'\''
                    else:
                        args_list[index] = args_list[index].split('!')[0]+'<>'+args_list[index].split('!')[1]
                
            #Combine to 1 string
            expression = args_list[0]
            if 'tag' in expression:
                expression = ""
            for (index, entry) in enumerate(args_list):
                if index != 0 and 'tag' not in entry:
                    if len(expression != 0):
                        expression = expression+' AND '+ entry
                    else:
                        expression = entry
            
            #execute query
            try:
                with self.con:
                    cur = self.con.cursor()
                    if len(expression) != 0:
                        cur.execute("SELECT * FROM ap WHERE "+expression)
                    else:
                        cur.execute("SELECT * FROM ap")
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
            tempList =  list(cur.fetchall())
            #Compare result with tag_list if necessary
            if tag_compare:
                comparedList = []
                for (index,ap_entry) in enumerate(tempList):
                    if ap_entry[0] in tag_result:
                        comparedList.append(ap_entry)
                tempList = comparedList
            #Prune thorugh list
            newList = []
            for i in range(len(tempList)):
                newList.append([])
                newList[i].append(tempList[i][0])
                newList[i].append({})
                newList[i][1]['region'] = tempList[i][1]
                newList[i][1]['firmware'] = tempList[i][2]
                newList[i][1]['version'] = tempList[i][3]
                newList[i][1]['number_radio'] = tempList[i][4]
                newList[i][1]['memory_mb'] = tempList[i][5]
                newList[i][1]['free_disk'] = tempList[i][6]
                newList[i][1]['supported_protocol'] = tempList[i][7]
                newList[i][1]['number_radio_free'] = tempList[i][8]
                #Get a list of tags
                cur.execute("SELECT name FROM location_tags WHERE ap_name=\'"+str(tempList[i][0])+"\'")
                tagList = cur.fetchall()
                tagString = ""
                for tag in tagList:
                    tagString += str(tag[0])+" "
                newList[i][1]['tags'] = tagString
            return newList
            
    def ap_list(self, args, tenant_id, user_id, project_id):
        if args['filter']:
            arg_filter = args['filter'][0]
        else:
            arg_filter = []
        arg_i = args['i']
        toPrint = self.ap_filter(arg_filter)
        message = ""
        for entry in toPrint:
            message += '\nName: '+str(entry[0])+'\n'
            if arg_i == True: #Print extra data
                for attr in entry[1]:
                    message += str(attr)+': '+str(entry[1][attr])+'\n'
        #return response
        response = {"status":True, "message":message}
        return response
    
    def ap_show(self, args, tenant_id, user_id, project_id):
        arg_name = args['ap-show'][0]
        toPrint = self.ap_filter('name='+arg_name)
        message = ""
        for entry in toPrint:
            message += '\nName: '+str(entry[0])+'\n'
            for attr in entry[1]:
                message += str(attr)+': '+str(entry[1][attr])+'\n'
        #return response
        response = {"status":True, "message":message}
        return response
                
    def ap_slice_modify(self, args, tenant_id, user_id, project_id):
        print "Not Yet Implemented"
        #return response
        response = {"status":False, "message":""}
        return response
    
    def ap_slice_restart(self, args, tenant_id, user_id, project_id): #UNTESTED, RUN AT OWN RISK
        slice_names = args['ap-slice-restart'] #Multiple Names
        if args['filter']:
            slice_names = []
            args_filter = args['filter'][0]
            slice_list = self.ap_slice_filter(args_filter)
            #Get list of slice_ids
            for entry in slice_list:
                slice_names.append(slice_list['ap-slice-id'])
        
        for entry in slice_names:
            #Get ap name
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(entry)+"\'")
                    ap_name = cur.fetchone()[0]
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
            
            print("Deleting Slice " + str(entry) + "...")
            self.ap_slice_delete({"ap-slice-delete":str(entry)})
            
            print("Recreating Slice " + str(entry) + "...")
            self.ap_slice_create({"ap":str(ap_name)})
            
            #return response
            response = {"status":True, "message":""}
            return response
    
    def ap_slice_add_tag(self, args, tenant_id, user_id, project_id):
        if not args['tag']:
            print('Error: Please specify a tag with --tag')
            sys.exit(1)
        else:
            tag = args['tag'][0]
        #Get list of slice_ids
        if args['filter']:
            slice_names = []
            args_filter = args['filter'][0]
            slice_list = self.ap_slice_filter(args_filter)
            #Get list of slice_ids
            for entry in slice_list:
                slice_names.append(entry['ap_slice_id'])
        else:
            slice_names = args['ap-slice-add-tag']
        
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        #Add tags
        for entry in slice_names:
            try:
                with mdb.connect('localhost', 'root', 'supersecret', 'aurora') as db:
                    to_execute = "INSERT INTO tenant_tags VALUES (\'"+str(tag[0])+"\', \'"+str(entry)+"\')"
                    
                    #TODO: Fix below syntax error
                    to_execute = "REPLACE INTO tenant_tags VALUES (\'%s\', \'%s\')" \
                                                 % (str(tag), str(slice_id))
                                                 
                    print to_execute
                    db.execute("INSERT INTO tenant_tags VALUES (\'"+str(tag)+"\', \'"+str(entry)+"\')")
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                
        #return response
        response = {"status":True, "message":""}
        return response     
        
    def ap_slice_remove_tag(self, args, tenant_id, user_id, project_id):
        if not args['tag']:
            print('Error: Please specify a tag with --tag')
            sys.exit(1)
        else:
            tag = args['tag'][0]
        #Get list of slice_ids
        if args['filter']:
            slice_names = []
            args_filter = args['filter'][0]
            slice_list = self.ap_slice_filter(args_filter)
            #Get list of slice_ids
            for entry in slice_list:
                slice_names.append(entry['ap_slice_id'])
        else:
            slice_names = args['ap-slice-remove-tag']
        
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        #Remove tags
        for entry in slice_names:
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("DELETE FROM tenant_tags WHERE name=\'"+str(tag)+"\' AND ap_slice_id=\'"+str(entry)+"\'")
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                
        #Return response
        response = {"status":True, "message":""}
        return response
    
    def ap_slice_create(self, args, tenant_id, user_id, project_id):
    
        pprint(args)
    
        if 'ap' in args:
            arg_ap = args['ap']
        else:
            arg_ap = None
        if args['filter']:
            arg_filter = args['filter'][0]
        else:
            arg_filter = None
        if 'file' in args:
            arg_file = args['file']
        else:
            arg_file = None
        if args['tag']:
            arg_tag = args['tag'][0]
        json_list = [] #If a file is provided for multiple APs, we need to split the file for each AP, saved here
        
        if arg_ap:
            aplist = arg_ap
        else: #We need to apply the filter
            result = self.ap_filter(arg_filter)
            aplist = []
            for entry in result:
                aplist.append(entry[0])
                
        #Initialize json_list structure (We do NOT yet have a plugin for VirtualWIFI/RadioInterfaces, just load and send for now)
        for i in range(len(aplist)):
            json_list.append({'VirtualInterfaces':[], 'VirtualBridges':[], 'RadioInterfaces':arg_file['VirtualWIFI']})
            
        #Send to plugin for parsing
        json_list = SlicePlugin(tenant_id, user_id, arg_tag).parseCreateSlice(arg_file, len(aplist), json_list)
        
        message = ""
        
        #Print json_list (for debugging)
        for entry in json_list:
            print '\n'
            print json.dumps(entry, indent=4, sort_keys=True)
            print '\n'
        
        #Dispatch
        for (index,json_entry) in enumerate(json_list):
            #Generate unique slice_id and add entry to database
            slice_uuid = uuid.uuid4()
            print slice_uuid
            self.auroraDB.slice_add(slice_uuid, tenant_id, aplist[index], project_id)
            message += "Slice "+str(index+1)+": "+str(slice_uuid)+'\n'
            #Add tags if present
            if args['tag']:
                self.ap_slice_add_tag({'ap-slice-add-tag':[str(slice_uuid)], 'tag': [arg_tag], 'filter':""}, tenant_id, user_id, project_id)
            #Dispatch (use slice_uuid as a message identifier)
            self.dispatch.dispatch(json_entry, aplist[index], slice_uuid)
        #Return response (message returns a list of uuids for created slices)
        
        response = {"status":True, "message":message}
        return response
    
    def ap_slice_delete(self, args, tenant_id, user_id, project_id):
        arg_name = args['ap-slice-delete'][0]
        
        config = {"slice":arg_name, "command":"delete_slice", "user":user_id}
        
        #Figure out which AP has the slice/change status to DELETING
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(arg_name)+"\'")
                ap_name = cur.fetchone()[0]
                cur.execute("UPDATE ap_slice SET status=\'DELETING\' WHERE ap_slice_id=\'"+str(arg_name)+"\'")
                #Remove tags
                cur.execute("DELETE FROM tenant_tags WHERE ap_slice_id=\'"+str(arg_name)+"\'")
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        #Dispatch
        #Generate unique message id
        message_id = uuid.uuid4()
        self.dispatch.dispatch(config, ap_name, str(message_id))
        
        #Return response
        response = {"status":True, "message":"Deleted "+str(arg_name)}
        return response
    
    def ap_slice_filter(self, arg_filter):
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        newList = [] #Result list
        if len(arg_filter) == 0: #No filter or tags
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT * FROM ap_slice")
                    tempList =  cur.fetchall()
                    pprint(tempList)
                    #Prune thorugh list
                    for i in range(len(tempList)):
                        newList.append({})
                        newList[i]['ap_slice_id'] = tempList[i][0]
                        newList[i]['tenant_id'] = tempList[i][1]
                        newList[i]['physical_ap'] = tempList[i][2]
                        newList[i]['project_id'] = tempList[i][3]
                        newList[i]['wnet_id'] = tempList[i][4]
                        newList[i]['status'] = tempList[i][5]
                        #Get a list of tags
                        cur.execute("SELECT name FROM tenant_tags WHERE ap_slice_id=\'"+str(tempList[i][0])+"\'")
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i]['tags'] = tagString
            
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        else: #Multiple arguments
            tag_compare = False #For tags, we need 2 queries and a quick result compare at the end
            tag_result = []
            args_list = arg_filter.split('&')
            for (index, entry) in enumerate(args_list):
                args_list[index] = entry.strip()
                #Filter for tags (NOT Query is not yet implemented (future work?), support for only 1 tag (USE 'OR' STATEMENT IN FUTURE FOR MULTIPLE))
                if 'tag' in args_list[index]:
                    tag_compare = True
                    try:
                        with self.con:
                            cur = self.con.cursor()
                            if '=' in args_list[index]:
                                cur.execute("SELECT ap_slice_id FROM tenant_tags WHERE name=\'"+args_list[index].split('=')[1]+"\'")
                            else:
                                print("Unexpected character in tag query. Please check syntax and try again!")
                                sys.exit(0)
                            tempresult = cur.fetchall()
                            for result in tempresult:
                                tag_result.append(result[0])
                                
                    except mdb.Error, e:
                        print "Error %d: %s" % (e.args[0], e.args[1])
                
                elif '=' in args_list[index]:
                    args_list[index] = args_list[index].split('=')[0]+'=\''+args_list[index].split('=')[1]+'\''
                elif '!' in args_list[index]:
                    args_list[index] = args_list[index].split('!')[0]+'<>\''+args_list[index].split('!')[1]+'\''
                
            #Combine to 1 string
            expression = args_list[0]
            if 'tag' in expression:
                expression = ""
            for (index, entry) in enumerate(args_list):
                if index != 0 and 'tag' not in entry:
                    if len(expression) != 0:
                        expression = expression+' AND '+ entry 
                    else:
                        expression = entry
            
            #Execute Query
            try:
                with self.con:
                    cur = self.con.cursor()
                    if len(expression) != 0:
                        cur.execute("SELECT * FROM ap_slice WHERE "+expression)
                    else:
                        cur.execute("SELECT * FROM ap_slice")
                    tempList = list(cur.fetchall())
                    #Compare result with tag_list if necessary
                    if tag_compare:
                        comparedList = []
                        for (index,slice_entry) in enumerate(tempList):
                            if slice_entry[0] in tag_result:
                                comparedList.append(slice_entry)
                        tempList = comparedList
                    #Prune thorugh list
                    for i in range(len(tempList)):
                        newList.append({})
                        newList[i]['ap_slice_id'] = tempList[i][0]
                        newList[i]['tenant_id'] = tempList[i][1]
                        newList[i]['physical_ap'] = tempList[i][2]
                        newList[i]['project_id'] = tempList[i][3]
                        newList[i]['wnet_id'] = tempList[i][4]
                        newList[i]['status'] = tempList[i][5]
                        #Get a list of tags
                        cur.execute("SELECT name FROM tenant_tags WHERE ap_slice_id=\'"+str(tempList[i][0])+"\'")
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i]['tags'] = tagString
            
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        
        return newList
        
    
    def ap_slice_list(self, args, tenant_id, user_id, project_id):
        print "args: ", args
        if args['filter']:
            arg_filter = args['filter'] #MK
      #      arg_filter = args['filter'][0]
        else:
            arg_filter = []
        arg_i = args['i']
        
        
        print "arg_filter: ", arg_filter
        
        newList = self.ap_slice_filter(arg_filter)

        message = ""
        if arg_i == False:
            for entry in newList:
                message += 'ap_slice_id: '+entry['ap_slice_id']+'\n\n'
        else:
            for entry in newList:
                for attr in entry:
                    message += str(attr)+': '+str(entry[attr])+'\n'
                message += '\n'
        
        #Return response
        response = {"status":True, "message":message}
        return response
                
    def ap_slice_show(self, args, tenant_id, user_id, project_id):
        arg_id = args['ap-slice-show'][0]
        return self.ap_slice_list({'filter':'ap_slice_id='+str(arg_id), 'i':True},\
                                  tenant_id, user_id, project_id)

    def wnet_add_wslice(self, args, tenant_id, user_id, project_id): #TODO:Slice filter integration
        arg_name = args['wnet-add-wslice'][0]
        arg_slice = args['slice'][0]
        
        print "arg_name:", arg_name
        print "arg_slice:", arg_slice
        
        #Send to database
        self.auroraDB.wnet_add_wslice(tenant_id, arg_slice, arg_name)
        
        #Return Response
        response = {"status":True, "message":""}
        return response

    def wnet_create(self, args, tenant_id, user_id, project_id):
        #Functionality is limited, placeholder for future expansions
        arg_name = args['wnet-create'][0]
        
        #Generate uuid
        arg_uuid = str(uuid.uuid4())
        #Send to database
        self.auroraDB.wnet_add(arg_uuid, arg_name, tenant_id, project_id)
        
        #Send Response
        response = {"status":True, "message":""}
        return response
    
    def wnet_delete(self, args, tenant_id, user_id, project_id): 
        arg_name = args['wnet-delete'][0]
        #Send to database
        self.auroraDB.wnet_remove(arg_name)
        
        #Send Response
        response = {"status":True, "message":""}
        return response
    
    def wnet_join_subnet(self, args, tenant_id, user_id, project_id): #TODO AFTER SAVI INTEGRATION
        arg_netname = args['wnet-join-subnet'][0]
        arg_wnetname = args['wnet_name'][0]
        #Send to database
        print('NOT YET IMPLEMENTED')
    
    def wnet_fetch(self, tenant_id):
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        if tenant_id == 0: #Admin, show all
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT * FROM wnet")
                    tempList =  cur.fetchall()
                    #Prune thorugh list
                    newList = []
                    for i in range(len(tempList)):
                        newList.append({})
                        newList[i]['wnet_id'] = tempList[i][0]
                        newList[i]['name'] = tempList[i][1]
                        newList[i]['tenant_id'] = tempList[i][2]
                        newList[i]['project_id'] = tempList[i][3]
                        
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                sys.exit(1)   
        else: #Match tenant_id
            try:
                with self.con:
                    cur = self.con.cursor()
                    cur.execute("SELECT * FROM wnet WHERE tenant_id=\'"+str(tenant_id)+"\'")
                    tempList =  cur.fetchall()
                    #Prune thorugh list
                    newList = []
                    for i in range(len(tempList)):
                        newList.append({})
                        newList[i]['wnet_id'] = tempList[i][0]
                        newList[i]['name'] = tempList[i][1]
                        newList[i]['tenant_id'] = tempList[i][2]
                        newList[i]['project_id'] = tempList[i][3]
                        
            except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
                sys.exit(1)
            
        return newList
    
    def wnet_remove_wslice(self, args, tenant_id, user_id, project_id): #TODO:Slice filter integration
        arg_name = args['wnet-remove-wslice'][0]
        arg_slice = args['slice'][0]
        #Send to database
        self.auroraDB.wnet_remove_wslice(tenant_id, arg_slice, arg_name)
        message = 'Slice with ap_slice_id ' + arg_slice + ' removed from wnet ' + arg_name
        #Send Response
        response = {"status":True, "message":message}
        return response
    
    def wnet_list(self, args, tenant_id, user_id, project_id):
        toPrint = self.wnet_fetch(tenant_id)
        message = ""
        for entry in toPrint:
            for attr in entry:
                message += str(attr)+': '+str(entry[attr])+'\n'
            message += '\n'
        
        #Return response
        response = {"status":True, "message":message}
        return response
            
    
    def wnet_show(self, args, tenant_id, user_id, project_id):
        arg_name = args['wnet-show'][0]
        toPrint = self.wnet_fetch(tenant_id)
        message = ""
        for entry in toPrint:
            if entry['name'] == arg_name:
                for attr in entry:
                    message += str(attr)+': '+str(entry[attr])+'\n'
                message += '\n'
        
        #Return response
        response = {"status":True, "message":message}
        return response

    def _wnet_show_wslices(self, wnet_name, tenant_id):
        """Helper method for other wnet classes.
        
        Return: A dictionary containing:
                {   "message":<NoneType if successful, something
                                if wnet doesn't exist>
                    "ap_slices":<NoneType if none, otherwise
                                  a tuple of tuples with ap_slice
                                  info related to specified wnet_name>
                }

        """
        return_dictionary = {}
        #DEBUG
        print "wnet_name: " + wnet_name
             
        try:
           with mdb.connect(mysql_host, mysql_username, mysql_password, mysql_db) as db:
                to_execute = "SELECT wnet_id FROM wnet WHERE tenant_id=\'" + str(tenant_id) + \
                             "\' AND name=\'"+str(wnet_name)+"\'"
                print to_execute
                db.execute(to_execute)
                wnet_id = db.fetchone()
                if not wnet_id:
                    # Build return_dictionary
                    return_dictionary["message"] = 'No wnet for tenant \'' + str(tenant_id) + \
                                                    '\' with name \'' + str(wnet_name) + '\'.\n'
                    return_dictionary["ap_slices"] = None
                    
                else:
                    wnet_id = wnet_id[0]
                    print "wnet_id: " + str(wnet_id)  
                    
                    to_execute = "SELECT * FROM ap_slice WHERE tenant_id=\'" + \
                                  str(tenant_id) + "\' AND wnet_id=\'"+str(wnet_id)+"\'"
                    print to_execute
                    db.execute(to_execute)
                    all_slices_tuple = db.fetchall()
                    print "all_slices_tuple: "
                    print all_slices_tuple
                    
                    # Build return_dictionary
                    if all_slices_tuple:
                        return_dictionary["message"] = None
                        return_dictionary["ap_slices"] = all_slices_tuple
                    else:
                        return_dictionary["message"] = 'No ap_slices in wnet \'' + str(wnet_name) + \
                                                        '\' for tenant_id \'' + str(tenant_id) + '\'.\n'
                        return_dictionary["ap_slices"] = None
       
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        return return_dictionary
        
    def wnet_show_wslices(self, args, tenant_id, user_id, project_id):
        """Method which shows the wslices associated with wnet"""
        message = ""
        # args can contain multiple wnet names
        for wnet_name in args['wnet-show-wslices']:
            wslices_dict = self._wnet_show_wslices(wnet_name, tenant_id)
            #DEBUG
            print "wslices_dict:1: "
            print wslices_dict
            
            if wslices_dict["message"]:
                # Either no wnet, or no ap_slices
                print 'Appending dictionary message'
                message += wslices_dict["message"]
            
            else:
                message += 'wnet \'' + str(wnet_name) + '\' contains :\n'
                for slice_tuple in wslices_dict["ap_slices"]:
                    slice_id = slice_tuple[0]
                    message += '\tslice with ap_slice_id \'' + slice_id + '\'\n'

        response = {"status":True, "message":message}
        return response 

    def wnet_remove_all(self, args, tenant_id, user_id, project_id):
        """Method which changes wnet of all ap_slices associated with wnet_name to NULL  
        """
        message = ""
        # args can contain multiple wnet names
        for wnet_name in args['wnet-remove-all']:
            wslices_dict = self._wnet_show_wslices(wnet_name, tenant_id)
            #DEBUG
            print "wslices_dict:2: "
            print wslices_dict
            
            if wslices_dict["message"]:
                # Either no wnet, or no ap_slices
                print 'Appending dictionary message'
                message += wslices_dict["message"]
            
            else:
                # Disassociate slice from wnet in database (assign its wnet Null)
                for slice_tuple in wslices_dict["ap_slices"]:
                    slice_id = slice_tuple[0]
                    self.auroraDB.wnet_remove_slice(tenant_id, slice_id, wnet_name)
                    message += 'Slice with ap_slice_id \'' + slice_id + \
                               '\' removed from wnet \'' + wnet_name + '\'\n'
            
        response = {"status":True, "message":message}
        return response  

    def wnet_add_tag(self, args, tenant_id, user_id, project_id):
        """Adds user-defined tags to a wnet"""
        message = ""
        if not args['tag']:
            message += "No tags specified.\n"
        else:
        # Handle more than one wnet
            for wnet_name in args['wnet-add-tag']:
                wslices_dict = self._wnet_show_wslices(wnet_name, tenant_id)
                print "wslices_dict:3: "
                print wslices_dict
                
                if wslices_dict["message"]:
                    # Either no wnet, or no ap_slices
                    print 'Appending dictionary message'
                    message += wslices_dict["message"]
                
                else:
                    # Add tags to sql table tenant_tags
                    message += 'Modifying slices in \'' + str(wnet_name) + '\':\n'
                    try:
                       with mdb.connect(mysql_host, mysql_username, mysql_password, mysql_db) as db:
                            for slice_tuple in wslices_dict["ap_slices"]:
                                # For every slice in wnet
                                slice_id = slice_tuple[0]
                                message += '\tslice with ap_slice_id \'' + slice_id + '\'\n'
                                
                                # Add (multiple) tags in MySQL db
                                for tag in args['tag']:
                                    to_execute = "REPLACE INTO tenant_tags VALUES (\'%s\', \'%s\')" \
                                                 % (str(tag), str(slice_id))
                                    print to_execute
                                    db.execute(to_execute)
                                
                            # Build rest of message (Not required if efficiency is key)
                            message += 'All slices now include tenant_tag(s) \''
                            message += '\' \''.join(args['tag'])
                            message += '\'.\n'         
                            
                        
                    except mdb.Error, e:
                        print "Error %d: %s" % (e.args[0], e.args[1])
                        sys.exit(1)
        response = {"status":True, "message":message}
        return response
    
    #Can move some of this functionality to auroraDB
    def wnet_remove_tag(self, args, tenant_id, user_id, project_id):
        """Removes user-defined tags from a wnet"""
        message = ""
        if not args['tag']:
            message += "No tags specified.\n"
        else:
        # Handle more than one wnet
            for wnet_name in args['wnet-remove-tag']:
                wslices_dict = self._wnet_show_wslices(wnet_name, tenant_id)
                #DEBUG
                print "wslices_dict:3: "
                print wslices_dict
                
                if wslices_dict["message"]:
                    # Either no wnet, or no ap_slices
                    print 'Appending dictionary message'
                    message += wslices_dict["message"]
                
                else:
                    # Add tags to sql table tenant_tags
                    message += 'Modifying slices in \'' + str(wnet_name) + '\':\n'
                    try:
                       with mdb.connect(mysql_host, mysql_username, mysql_password, mysql_db) as db:
                            for slice_tuple in wslices_dict["ap_slices"]:
                                # For every slice in wnet
                                slice_id = slice_tuple[0]

                                # Add (multiple) tags in MySQL db
                                for tag in args['tag']:
                                    to_execute = "SELECT name FROM tenant_tags WHERE ap_slice_id = \'" + \
                                                 str(slice_id) + "\'"
                                    db.execute(to_execute)
                                    names = db.fetchall()
                                    print names
                                    if names:
                                        for name in names:
                                            if name[0] == tag:
                                                # This slice has a tag that matches, delete.
                                                to_execute = "DELETE FROM tenant_tags WHERE " + \
                                                             "name = \'%s\' AND ap_slice_id = \'%s\'" \
                                                             % (str(tag), str(slice_id))
                                                print to_execute
                                                db.execute(to_execute)
                                                message += '\tslice with ap_slice_id \'' + \
                                                           slice_id + '\'\n'
                                
                            # Build rest of message (Not required if efficiency is key)
                            message += 'All slices no longer include tenant_tag(s) \''
                            message += '\' \''.join(args['tag'])
                            message += '\'.\n'
                    except mdb.Error, e:
                        print "Error %d: %s" % (e.args[0], e.args[1])
                        sys.exit(1) 
        response = {"status":True, "message":message}
        return response

#For Testing
#Manager().parseargs('ap-slice-create', {'filter':['region=mcgill & number_radio<2 & version<1.1 & number_radio_free!2 & supported_protocol=a/b/g'], 'file':['json/slicetemp.json'], 'tag':['first']},1,1,1)
#Manager().parseargs('ap-slice-create', {'ap':['of1', 'of2', 'of3', 'of4'],'file':['json/slicetemp.json'], 'tag':['first']},1,1,1)
#Manager().parseargs('ap-slice-create', {'ap':['of1'],'file':['json/slicetemp.json'], 'tag':['first']},1,1,1)
#Manager().parseargs('ap-list', {'filter':['name=openflow & tag=mc838'], 'i':True},1,1,1)
#Manager().parseargs('ap-slice-list', {'filter':['tag=first & physical_ap=openflow'], 'i':True}, 1,1,1)
#Manager().parseargs('wnet_show', {'wnet-show':['wnet-1']}, 0,1,1)
#Manager().parseargs('ap-slice-add-tag', {'filter':['ap_slice_id=1'], 'tag':'testadding'},1,1,1)
#Manager().parseargs('ap-slice-remove-tag', {'filter':['ap_slice_id=1'], 'tag':'testadding'},1,1,1)
#Manager().parseargs('wnet-create', {'wnet-create':['testadding']},1,1,1)
#Manager().parseargs('wnet-delete', {'wnet-delete':['testadding']},1,1,1)
#Manager().parseargs('wnet-add-wslice', {'wnet-add-wslice':['wnet-1'], 'slice':['1']},1,1,1)
#Manager().parseargs('wnet-remove-wslice', {'wnet-remove-wslice':['wnet-1'], 'slice':['1']},1,1,1)
