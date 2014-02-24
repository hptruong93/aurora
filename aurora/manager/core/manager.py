# Aurora Manager Functions
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json
import logging
from pprint import pprint, pformat
import sys
import time
import uuid

import MySQLdb as mdb

from aurora_db import *
import ap_monitor
from cls_logger import get_cls_logger
import dispatcher
import ap_provision.http_srv as provision
import request_verification as Verify
import slice_plugin

LOGGER = logging.getLogger(__name__)


class Manager(object):
    #Dispatcher variables

    MYSQL_HOST = 'localhost'
    MYSQL_USERNAME = 'root'
    MYSQL_PASSWORD = 'supersecret'
    MYSQL_DB = 'aurora'

    def __init__(self):
        self.LOGGER = get_cls_logger(self)
        self.LOGGER.info("Constructing Manager...")

        ### Dispatcher variables
        host = 'localhost'
        username = 'outside_world'
        password = 'wireless_access'
        self.mysql_host = self.MYSQL_HOST #host
        self.mysql_username = self.MYSQL_USERNAME #'root'
        self.mysql_password = self.MYSQL_PASSWORD #'supersecret'
        self.mysql_db = self.MYSQL_DB #'aurora'

        #Initialize AuroraDB Object
        self.auroraDB = AuroraDB(self.mysql_host,
                                 self.mysql_username,
                                 self.mysql_password,
                                 self.mysql_db)
        #Comment for testing without AP
        self.dispatch = dispatcher.Dispatcher(host,
                                              username,
                                              password,
                                              self.mysql_username,
                                              self.mysql_password,
                                              self.auroraDB)

        self.apm = ap_monitor.APMonitor(self.dispatch, self.auroraDB, self.mysql_host, self.mysql_username, self.mysql_password)

        provision.run()

    def __del__(self):
        self.LOGGER.info("Destructing Manager...")


    def stop(self):
        self.apm.stop()
        self.dispatch.stop()
        provision.stop()

    def parseargs(self, function, args, tenant_id, user_id, project_id):
        # args is a generic dictionary passed to all functions (each function is responsible for parsing
        # their own arguments
        function = function.replace('-', '_') #For functions in python
        response = getattr(self, function)(args, tenant_id, user_id, project_id)
        return response

    #STILL NEED TO IMPLEMENT TAG SEARCHING (location_tags table), maybe another connection with intersection?
    def ap_filter(self, args):
        try:
            self.con = mdb.connect(self.mysql_host,
                                   self.mysql_username,
                                   self.mysql_password,
                                   self.mysql_db)
        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
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
                        newList[i][1]['number_slice_free'] = tempList[i][9]
                        newList[i][1]['status'] = tempList[i][10]
                        #Get a list of tag
                        cur.execute("SELECT name FROM location_tags WHERE ap_name=\'"+str(tempList[i][0])+"\'")
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i][1]['tags'] = tagString
                    return newList
            except mdb.Error, e:
                self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
        else: #Multiple arguments (name=openflow & firmware=openwrt & region=mcgill & number_radio>1)
            tag_compare = False #For tags, we need 2 queries and a quick result compare at the end
            tag_result = []
            args_list = args.split('&')
            for (index, entry) in enumerate(args_list):
                args_list[index] = entry.strip()
                 #Filter for tags (NOT Query is not yet implemented (future work?),
                 #support for only 1 tag (USE 'OR' STATEMENT IN FUTURE FOR MULTIPLE))
                if 'tag' in args_list[index] or 'location' in args_list[index]:
                    tag_compare = True
                    try:
                        with self.con:
                            cur = self.con.cursor()
                            if '=' in args_list[index]:
                                cur.execute("SELECT ap_name FROM location_tags WHERE name=\'"+\
                                            args_list[index].split('=')[1]+"\'")
                            else:
                                self.LOGGER.warning("Unexpected character in tag query. Please check syntax and try again!")
                                sys.exit(0)
                            tempresult = cur.fetchall()
                            for result in tempresult:
                                tag_result.append(result[0])

                    except mdb.Error, e:
                        self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))

                elif '=' in args_list[index]:
                    if (args_list[index].split('=')[0] == "name")           or \
                       (args_list[index].split('=')[0] == "firmware")       or \
                       (args_list[index].split('=')[0] == "region")         or \
                       (args_list[index].split('=')[0] == "supported_protocol") or \
                       (args_list[index].split('!')[0] == "status"):
                        args_list[index] = args_list[index].split('=')[0]+'=\'' + \
                                           args_list[index].split('=')[1]+'\''
                    else:
                        args_list[index] = args_list[index].split('!')[0]+'<>' + \
                                           args_list[index].split('!')[1]
                elif '!' in args_list[index]:
                    if (args_list[index].split('!')[0] == "name")           or \
                       (args_list[index].split('!')[0] == "firmware")       or \
                       (args_list[index].split('!')[0] == "region")         or \
                       (args_list[index].split('!')[0] == "supported_protocol") or \
                       (args_list[index].split('!')[0] == "status"):
                        args_list[index] = args_list[index].split('!')[0]+'<>\'' + \
                                           args_list[index].split('!')[1]+'\''
                    else:
                        args_list[index] = args_list[index].split('!')[0]+'<>' + \
                                           args_list[index].split('!')[1]

            #Combine to 1 string
            expression = args_list[0]
            if 'tag' in expression or 'location' in expression:
                expression = ""
            for (index, entry) in enumerate(args_list):
                #if index != 0 and 'tag' or 'location' not in entry:
                if index != 0 and 'tag' not in entry and 'location' not in entry:
                    if len(expression) != 0:
                        expression = expression+' AND '+ entry
                    else:
                        expression = entry

            #execute query
            try:
                with self.con:
                    cur = self.con.cursor()
                    tempList = []
                    if len(expression) != 0:
                        cur.execute("SELECT * FROM ap WHERE "+expression)
                    else:
                        cur.execute("SELECT * FROM ap")
                    tempList = list(cur.fetchall())
            except mdb.Error, e:
                self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))

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
                newList[i][1]['number_slice_free'] = tempList[i][9]
                newList[i][1]['status'] = tempList[i][10]
                #Get a list of tags
                cur.execute("SELECT name FROM location_tags WHERE ap_name=\'"+str(tempList[i][0])+"\'")
                tagList = cur.fetchall()
                tagString = ""
                for tag in tagList:
                    tagString += str(tag[0])+" "
                newList[i][1]['tags'] = tagString
            return newList

    def ap_list(self, args, tenant_id, user_id, project_id):
        #TODO: Verify filter passes correctly
        if args['filter']:
            arg_filter = args['filter'][0]
        else:
            arg_filter = []
        arg_i = args['i']
        toPrint = self.ap_filter(arg_filter)
        message = ""
        for entry in toPrint:
            if not arg_i:
                message += "%5s: %s - %s\n" % ("Name", entry[0], entry[1]['status'])
            else: #Print extra data
                message += "%19s: %s - %s\n" % ("Name", entry[0], entry[1]['status'])
                for attr in entry[1]:
                    if attr != 'status':
                        message += "%19s: %s\n" % (attr, entry[1][attr])
                message += '\n'

        #return response
        response = {"status":True, "message":message}
        return response

    def ap_show(self, args, tenant_id, user_id, project_id):
        #TODO: Verify filter passes correctly
        arg_name = args['ap-show'][0]
        toPrint = self.ap_filter('name='+arg_name)
        message = ""
        for entry in toPrint:
            message += "%19s: %s\n" % ("Name", entry[0])
            for attr in entry[1]:
                if attr != 'status':
                    message += "%19s: %s\n" % (attr, entry[1][attr])
            message += '\n'
        #return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_modify(self, args, tenant_id, user_id, project_id):
        self.LOGGER.warning("Not Yet Implemented")
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

        for ap_slice_id in slice_names:
            #Get ap name
            try:
                with mdb.connect(self.mysql_host,
                                 self.mysql_username,
                                 self.mysql_password,
                                 self.mysql_db) as db:
                    db.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id='%s'" % ap_slice_id )
                    ap_name = db.fetchone()[0]
            except mdb.Error, e:
                self.LOGGER.error( "Error %d: %s" % (e.args[0], e.args[1]))

            #Note: This will remove all associated tenant_tags
            self.LOGGER.info("Deleting Slice " + str(ap_slice_id) + "...")
            self.ap_slice_delete({"ap-slice-delete":str(ap_slice_id)})

            self.LOGGER.info("Recreating Slice " + str(ap_slice_id) + "...")
            self.ap_slice_create({"ap":str(ap_name)})

            #return response
            response = {"status":True, "message":""}
            return response

    def ap_slice_add_tag(self, args, tenant_id, user_id, project_id):
        message = ""
        if not args['tag']:
            err_msg = 'Error: Please specify a tag with --tag\n'
            self.LOGGER.error(err_msg)
            response = {"status":False, "message": err_msg}
            return response
        else:
            tags = args['tag']
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

        #Add tags
        for slice_id in slice_names:
            if self.auroraDB.wslice_belongs_to(tenant_id, project_id, slice_id):
                for tag in tags:
                    message += self.auroraDB.wslice_add_tag(slice_id, tag)
            else:
                err_msg = "Error: You have no slice '%s'." % slice_id
                message += err_msg + '\n'

        #return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_remove_tag(self, args, tenant_id, user_id, project_id):
        message = ""
        if not args['tag']:
            err_msg = 'Error: Please specify a tag with --tag\n'
            self.LOGGER.error(err_msg)
            response = {"status":False, "message": err_msg}
            return response
        else:
            tags = args['tag']
        #Get list of slice_ids
        if args['filter']:
            slice_names = []
            args_filter = args['filter'][0]
            slice_list = self.ap_slice_filter(args_filter) #TODO: Check this still works with filter
            #Get list of slice_ids
            for entry in slice_list:
                slice_names.append(entry['ap_slice_id'])
        else:
            slice_names = args['ap-slice-remove-tag']

        #Remove tags
        for slice_id in slice_names:
            if self.auroraDB.wslice_belongs_to(tenant_id, project_id, slice_id):
                for tag in tags:
                    message += self.auroraDB.wslice_remove_tag(slice_id, tag)
            else:
                err_msg = "Error: You have no slice '%s'." % slice_id
                message += err_msg + '\n'

        #Return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_create(self, args, tenant_id, user_id, project_id):
        message = ""
        self.LOGGER.debug(pformat(args))

        arg_ap = None
        arg_filter = None
        arg_file = None
        arg_tag = None
        if 'ap' in args:
            arg_ap = args['ap']
        if args['filter']:
            arg_filter = args['filter'][0]
        if 'file' in args:
            arg_file = args['file']
        if args['tag']:
            arg_tag = args['tag'][0]

        json_list = [] #If a file is provided for multiple APs,
                       #we need to split the file for each AP, saved here

        if arg_ap:
            aplist = arg_ap
        elif arg_filter: #We need to apply the filter
            result = self.ap_filter(arg_filter)
            aplist = []
            for entry in result:
                aplist.append(entry[0])
        else:
            err_msg = "Error: Specify an access point or filter\n"
            self.LOGGER.error(err_msg)
            response = {"status":False, "message":err_msg}
            return response

        if 'TrafficAttributes' not in arg_file.keys():
            arg_file['TrafficAttributes'] = {}

        #Initialize json_list structure (We do NOT yet have a plugin for
        #VirtualWIFI/RadioInterfaces, just load and send for now)
        for i in range(len(aplist)):
            json_list.append({'VirtualInterfaces':[],
                              'VirtualBridges':[],
                              'RadioInterfaces':arg_file['VirtualWIFI'],
                              'TrafficAttributes':arg_file['TrafficAttributes']})

        #Send to plugin for parsing
        try:
            json_list = slice_plugin.SlicePlugin(tenant_id,
                                    user_id,
                                    arg_tag).parse_create_slice(arg_file,
                                                                len(aplist),
                                                                json_list)

        except Exception as e:
            self.LOGGER.error(e.message)
            response = {"status":False, "message":e.message}
            return response

        # Print json_list (for debugging)
        for i, entry in enumerate(json_list):
            #print '\n'
            self.LOGGER.debug(json.dumps(entry, indent=4, sort_keys=True))
            #print '\n'
    #        with open("core/json/wifi__%s.json" % i,"w") as f:
    #            print "Writing file json/wifi__%s.json\n" % i
    #            json.dump(entry, f, indent=4)
    #            f.flush()
    #            f.close()


        add_success = True
        #Dispatch
        for (index,json_entry) in enumerate(json_list):
            #Generate unique slice_id and add entry to database
            slice_uuid = uuid.uuid4()
            json_entry['slice'] = str(slice_uuid)
            
            #Verify adding process. See request_verification for more information
            error = Verify.verifyOK(aplist[index], tenant_id, json_entry)
            #error = None #For testing
            #An error message is retuned if there is any problem, else None is returned.

            #Get SSID of slice to be created, only first is captured
            ap_slice_ssid = None
            for d_entry in json_entry['config']['RadioInterfaces']:
                if d_entry['flavor'] == 'wifi_bss':
                    ap_slice_ssid = d_entry['attributes']['name']
                    break

            if error is None: #There is no error
                error = self.auroraDB.wslice_add(slice_uuid, ap_slice_ssid, tenant_id, aplist[index], project_id)
            
                if error is not None: #There is an error
                    message += error + "\n"
                    add_success = False
                else:
                    message += "Adding slice %s: %s\n" % (index + 1, slice_uuid)
            
                    #Add tags if present
                    if args['tag']:
                        self.ap_slice_add_tag({'ap-slice-add-tag':[slice_uuid],
                                        'tag': [arg_tag],
                                        'filter':""},
                                        tenant_id, user_id, project_id)
                    #Dispatch (use slice_uuid as a message identifier)
                    self.dispatch.dispatch(json_entry, aplist[index], str(slice_uuid))
            else:
                message += error + "\n"
                add_success = False
        
        #Return response (message returns a list of uuids for created slices)
        response = {"status":add_success, "message":message}
        return response

    def ap_slice_delete(self, args, tenant_id, user_id, project_id):
        #TODO: Remove tags associated with deleted slices
        message = ""

        args_all = args['all']
        if args_all:
            arg_filter = "status!DELETED"
            ap_slice_dict= self.ap_slice_filter(arg_filter, tenant_id)
            ap_slice_list = []
            for entry in ap_slice_dict:
                ap_slice_list.append(entry['ap_slice_id'])

        else:
            ap_slice_list = args['ap-slice-delete']

      #  self.LOGGER.debug("ap_slice_list:",ap_slice_list)

        if not ap_slice_list:
            message += " None to delete\n"

        for ap_slice_id in ap_slice_list:
            config = {"slice":ap_slice_id, "command":"delete_slice", "user":user_id}

            my_slice = self.auroraDB.wslice_belongs_to(tenant_id, project_id, ap_slice_id)
            if not my_slice:
                message += "No slice '%s'\n" % ap_slice_id
                if ap_slice_id == ap_slice_list[-1]:
                    response = {"status":False, "message":message}
                    return response
                else:
                    continue
            try:
                arg_filter = "ap_slice_id=%s&status=DELETED" % ap_slice_id
                slice_list = self.ap_slice_filter(arg_filter, tenant_id)
                if slice_list:
                    message += "Slice already deleted: '%s'\n" % ap_slice_id
                    continue
                else:
                    ap_name = self.auroraDB.get_wslice_physical_ap(ap_slice_id)
            except Exception as e:
                response = {"status":False, "message":message + e.message}
                return response
            message += self.auroraDB.wslice_delete(ap_slice_id)

            #Dispatch
            #Generate unique message id
            self.LOGGER.debug("Launching dispatcher")
            self.dispatch.dispatch(config, ap_name)

        #Return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_filter(self, arg_filter, tenant_id):
        # NOTE: LOCATION FILTERING IS HACKED BY APPENDING TO TENANT TAGS
        #       This means it is possible that by typing a location field,
        #       the user may get results that have the tagged value in
        #       tenant_tags value instead of location_tags exclusively
        try:
            self.con = mdb.connect(self.mysql_host,
                                   self.mysql_username,
                                   self.mysql_password,
                                   self.mysql_db) #Change address
        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
            sys.exit(1)
        newList = [] #Result list
        if len(arg_filter) == 0: #No filter or tags
            try:
                with self.con:
                    cur = self.con.cursor()
                    if tenant_id == 0:
                        cur.execute("SELECT * FROM ap_slice")
                    else:
                        cur.execute( "SELECT * FROM ap_slice WHERE "
                                     "tenant_id = '%s'" % tenant_id )
                    tempList =  cur.fetchall()
                    #pprint(tempList)
                    #Prune thorugh list
                    for i in range(len(tempList)):
                        newList.append({})
                        newList[i]['ap_slice_id'] = tempList[i][0]
                        newList[i]['ap_slice_ssid'] = tempList[i][1]
                        newList[i]['tenant_id'] = tempList[i][2]
                        newList[i]['physical_ap'] = tempList[i][3]
                        newList[i]['project_id'] = tempList[i][4]
                        newList[i]['wnet_id'] = tempList[i][5]
                        newList[i]['status'] = tempList[i][6]
                        #Get a list of tags
                        cur.execute( "SELECT name FROM tenant_tags WHERE "
                                     "ap_slice_id = '%s'" % tempList[i][0] )
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        cur.execute( "SELECT name FROM location_tags WHERE "
                                     "ap_name = '%s'" % tempList[i][3] )
                        tagList = cur.fetchall()
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i]['tags'] = tagString

            except mdb.Error, e:
                self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
        else: #Multiple arguments
            tag_compare = False #For tags, we need 2 queries and a quick result compare at the end
            tag_result = []
            args_list = arg_filter.split('&')
           # print "args_list:", args_list
            for (index, entry) in enumerate(args_list):
                args_list[index] = entry.strip()
                if args_list[index] == '':
                    continue
                #Filter for tags (NOT Query is not yet implemented (future work?),
                #support for only 1 tag (USE 'OR' STATEMENT IN FUTURE FOR MULTIPLE))
                if 'tag' in args_list[index] or 'location' in args_list[index]:
                    #This now supports filters like --filter tag=mcgill.
                    #Should it be instead --filter location=mcgill?
                    tag_compare = True
                    try:
                        with self.con:
                            cur = self.con.cursor()
                            if '=' in args_list[index]:
                                cur.execute( "SELECT ap_slice_id FROM tenant_tags WHERE "
                                             "name = '%s'" % args_list[index].split('=')[1] )
                                tempresult = cur.fetchall()
                                for result in tempresult:
                                    tag_result.append(result[0])
                                cur.execute( "SELECT ap_name FROM location_tags WHERE "
                                             "name = '%s'" % args_list[index].split('=')[1] )
                                ap_locations = cur.fetchall()
                                for (i, location) in enumerate(ap_locations):
                                    self.LOGGER.debug("Looking for location info:", location)
                                    if tenant_id == 0:
                                        cur.execute( "SELECT ap_slice_id FROM ap_slice WHERE "
                                                     "physical_ap = '%s'" % location[0] )
                                    else:
                                        cur.execute( "SELECT ap_slice_id FROM ap_slice WHERE "
                                                     "tenant_id = '%s' AND "
                                                     "physical_ap = '%s'" % (tenant_id, location[0]) )
                                    phys_ap = cur.fetchall()
                                    self.LOGGER.debug("phys_ap:", phys_ap)
                                    for result in phys_ap:
                                        if result[0] not in tag_result:
                                            tag_result.append(result[0])
                            else:
                                raise Exception("Unexpected character in tag query. "
                                                "Please check syntax and try again!")


                    except mdb.Error, e:
                        self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))

                elif '=' in args_list[index]:
                    args_list[index] = "%s='%s'" % (args_list[index].split('=')[0],
                                                    args_list[index].split('=')[1])
                elif '!' in args_list[index]:
                    args_list[index] = "%s<>'%s'" % (args_list[index].split('!')[0],
                                                     args_list[index].split('!')[1])
                else:
                    raise Exception("Error: Incorrect filter syntax.\n")
            #Combine to 1 string
            expression = args_list[0]
            if 'tag' in expression or 'location' in expression:
                expression = ""
            for (index, entry) in enumerate(args_list):
                if index != 0 and 'tag' not in entry  and 'location' not in entry:
                    if len(expression) != 0:
                        expression = expression+' AND '+ entry
                    else:
                        expression = entry
            self.LOGGER.debug("SQL Filter:",expression)

            #Execute Query
            try:
                with self.con:
                    cur = self.con.cursor()
                    #TODO: Allow admin to see all (tenant_id of 0)
                    if len(expression) != 0:
                        cur.execute( ("SELECT * FROM ap_slice WHERE "
                                     "tenant_id = '%s' AND " % tenant_id) + expression )
                    else:
                        cur.execute( "SELECT * FROM ap_slice WHERE "
                                     "tenant_id = '%s'" % tenant_id )
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
                        newList[i]['ap_slice_ssid'] = tempList[i][1]
                        newList[i]['tenant_id'] = tempList[i][2]
                        newList[i]['physical_ap'] = tempList[i][3]
                        newList[i]['project_id'] = tempList[i][4]
                        newList[i]['wnet_id'] = tempList[i][5]
                        newList[i]['status'] = tempList[i][6]
                        #Get a list of tags
                        cur.execute("SELECT name FROM tenant_tags WHERE ap_slice_id=\'" + \
                                    str(tempList[i][0])+"\'")
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i]['tags'] = tagString

            except mdb.Error, e:
                self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))

        return newList


    def ap_slice_list(self, args, tenant_id, user_id, project_id):
        message = ""
        if args['filter']:
            arg_filter = args['filter'][0]
        else:
            arg_filter = ""
        arg_i = args['i']
        arg_a = args['a']
        if not arg_a:
            arg_filter += "&status!DELETED"
        self.LOGGER.debug("arg_filter: ", arg_filter)

        try:
            newList = self.ap_slice_filter(arg_filter, tenant_id)
        except Exception as e:
            message += e.message
            self.LOGGER.error(e)
            response = {"status":False, "message":message}
            return response
        if not newList:
            message += " None\n"
        for entry in newList:
            message += "%12s: %s" % ("ap_slice_id", entry['ap_slice_id'])
            if not arg_i:
                message += " ('%s' on %s) - %s\n" % (entry['ap_slice_ssid'], entry['physical_ap'], entry['status'])

            else:
                message += " '%s'\n" % entry['ap_slice_ssid']
                for key,value in entry.iteritems():
                    if key != 'ap_slice_id' and key != 'ap_slice_ssid':
                        message += "%12s: %s\n" % (key, value)
                active_time, bytes_sent = self.auroraDB.get_wslice_status(entry['ap_slice_id'])
                message += "(%12s): %s\n" % ("active_time", active_time)
                message += "(%12s): %s\n" % ("bytes_sent", bytes_sent)
                message += '\n'

        #Return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_show(self, args, tenant_id, user_id, project_id):
        message = ""
        for arg_id in args['ap-slice-show']:
            if self.auroraDB.wslice_belongs_to(tenant_id, project_id, arg_id):
                message += self.ap_slice_list({'filter':['ap_slice_id=%s' % arg_id,],
                                           'i':True,
                                           'a':True},
                                          tenant_id, user_id, project_id)['message']
            else:
                message += "Error: You have no slice '%s'.\n" % arg_id
            if arg_id == args['ap-slice-show'][-1]:
                response = {"status":False, "message": message}
                return response

        response = {"status":True, "message": message}
        return response


    def wnet_add_wslice(self, args, tenant_id, user_id, project_id):
        message = ""
        #TODO:Slice filter integration
        arg_name = args['wnet-add-wslice'][0]
        if not args['slice']:
            err_msg = "Error: No slices specified.\n"
            response = {"status":False, "message":err_msg}
            return response

        for arg_slice in args['slice']:

            self.LOGGER.debug("arg_name:", arg_name)
            self.LOGGER.debug("arg_slice:", arg_slice)

            my_slice = self.auroraDB.wslice_belongs_to(tenant_id, project_id, arg_slice)
            my_wnet = self.auroraDB.wnet_belongs_to(tenant_id, project_id, arg_name)

            #Send to database
            if my_slice and my_wnet:
                if not self.auroraDB.wslice_is_deleted(arg_slice):
                    message += self.auroraDB.wnet_add_wslice(tenant_id, arg_slice, arg_name)
                else:
                    message += "Error: Cannot add deleted slice '%s'" % arg_slice
            else:
                if not my_slice:
                    message += "Error: You have no slice '%s'.\n" % arg_slice
                else:
                    message += "Error: You have no wnet '%s'.\n" % arg_name
                response = {"status":False, "message":message}
                return response
        #Return Response
        response = {"status":True, "message":message}
        return response

    def wnet_create(self, args, tenant_id, user_id, project_id):
        message = ""
        #Functionality is limited, placeholder for future expansions
        arg_name = args['wnet-create'][0]

        #Generate uuid
        arg_uuid = uuid.uuid4()

        #Send to database
        message += self.auroraDB.wnet_add(arg_uuid, arg_name, tenant_id, project_id)

        #Send Response
        response = {"status":True, "message":message}
        return response

    def wnet_delete(self, args, tenant_id, user_id, project_id):
        arg_name = args['wnet-delete'][0]

        #Send to database
        try:
            message = self.auroraDB.wnet_remove(arg_name, tenant_id)
        except Exception as e:
            response = {"status":False, "message":e.message}
            return response
        #Send Response
        response = {"status":True, "message":message}
        return response

    def wnet_join_subnet(self, args, tenant_id, user_id, project_id):
        #TODO AFTER SAVI INTEGRATION
        arg_netname = args['wnet-join-subnet'][0]
        arg_wnetname = args['wnet_name'][0]

        #Send to database
        self.LOGGER.warning('NOT YET IMPLEMENTED')

    def wnet_remove_wslice(self, args, tenant_id, user_id, project_id):
        #TODO:Slice filter integration
        message = ""
        arg_name = args['wnet-remove-wslice'][0]
        if not args['slice']:
            err_msg = "No slice specified.\n"
            response = {"status":False, "message":err_msg}
            return response

        for arg_slice in args['slice']:
            try:
                my_slice = self.auroraDB.wslice_belongs_to(tenant_id, project_id, arg_slice)
                my_wnet = self.auroraDB.wnet_belongs_to(tenant_id, project_id, arg_name)

                if my_slice and my_wnet:
                    if not self.auroraDB.wslice_is_deleted(arg_slice):
                        message += self.auroraDB.wnet_remove_wslice(tenant_id, arg_slice, arg_name)
                    else:
                        message += "Error: Cannot add deleted slice '%s'" % arg_slice

                else:
                    if not my_slice:
                        message += "Error: You have no slice '%s'.\n" % arg_slice
                    else:
                        message += "Error: You have no wnet '%s'.\n" % arg_name
                    response = {"status":False, "message":message}
                    return response

            except Exception as e:
                response = {"status":False, "message":e.message}
                return response

            #Send to database
          #  message += self.auroraDB.wnet_remove_wslice(tenant_id, arg_slice, arg_name)
          #  message = "Slice '%s' removed from '%s'.\n" % (arg_slice, arg_name)

        #Send Response
        response = {"status":True, "message":message}
        return response

    def wnet_list(self, args, tenant_id, user_id, project_id):
        """Lists the wnets available to tenant"""
        arg_i = args['i']
        try:
            wnet_to_print = self.auroraDB.get_wnet_list(tenant_id)
        except Exception as e:
            response = {"status":False, "message":e.message}
            return response

        message = ""
        for entry in wnet_to_print:
            if not arg_i:
                message += "%5s: %s\n" % ("Name", entry['name'])
            else: #Print extra data
                message += "%11s: %s\n" % ("Name", entry['name'])
                for key,value in entry.iteritems():
                    if key != 'name':
                        message += "%11s: %s\n" % (key, value)
                message += '\n'
        #return response
        response = {"status":True, "message":message}
        return response

    def wnet_show(self, args, tenant_id, user_id, project_id):
        arg_i = args['i']
        arg_wnet = args['wnet-show'][0]

        try:
            wnet_to_print = self.auroraDB.get_wnet_list(tenant_id, arg_wnet)

            slices_to_print = self.auroraDB.get_wnet_slices(arg_wnet, tenant_id)
        except Exception as e:
            self.LOGGER.error(e)
            response = {"status":False, "message":e.message}
            return response

        message = ""
        for entry in wnet_to_print:
            message += "%13s: %s\n" % ("Name", entry['name'])
            for key,value in entry.iteritems():
                if key != 'name':
                    message += "%13s: %s\n" % (key, value)
            message += '\n'
        message += "Associated slices:\n"
        if not slices_to_print:
            message += " None\n"
        for entry in slices_to_print:
            message += "%13s: %s\n" % ("ap_slice_id", entry['ap_slice_id'])
            if arg_i:
                for key,value in entry.iteritems():
                    if key != 'ap_slice_id':
                        message += "%13s: %s\n" % (key, value)
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
        self.LOGGER.debug("wnet_name: " + wnet_name)

        try:
           with mdb.connect(self.mysql_host,
                            self.mysql_username,
                            self.mysql_password,
                            self.mysql_db) as db:
                to_execute = "SELECT wnet_id FROM wnet WHERE tenant_id=\'" + str(tenant_id) + \
                             "\' AND name=\'"+str(wnet_name)+"\'"
                self.LOGGER.debug(to_execute)
                db.execute(to_execute)
                wnet_id = db.fetchone()
                if not wnet_id:
                    # Build return_dictionary
                    return_dictionary["message"] = 'No wnet for tenant \'' + str(tenant_id) + \
                                                    '\' with name \'' + str(wnet_name) + '\'.\n'
                    return_dictionary["ap_slices"] = None

                else:
                    wnet_id = wnet_id[0]
                    self.LOGGER.debug("wnet_id: " + str(wnet_id))

                    to_execute = "SELECT * FROM ap_slice WHERE tenant_id=\'" + \
                                  str(tenant_id) + "\' AND wnet_id=\'"+str(wnet_id)+"\'"
                    self.LOGGER.debug(to_execute)
                    db.execute(to_execute)
                    all_slices_tuple = db.fetchall()
                    self.LOGGER.debug("all_slices_tuple: ")
                    self.LOGGER.debug(all_slices_tuple)

                    # Build return_dictionary
                    if all_slices_tuple:
                        return_dictionary["message"] = None
                        return_dictionary["ap_slices"] = all_slices_tuple
                    else:
                        return_dictionary["message"] = 'No ap_slices in wnet \'' + str(wnet_name) + \
                                                        '\' for tenant_id \'' + str(tenant_id) + '\'.\n'
                        return_dictionary["ap_slices"] = None

        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
            sys.exit(1)

        return return_dictionary

    def wnet_show_wslices(self, args, tenant_id, user_id, project_id):
        """Method which shows the wslices associated with wnet"""
        message = ""
        # args can contain multiple wnet names
        for wnet_name in args['wnet-show-wslices']:
            wslices_dict = self._wnet_show_wslices(wnet_name, tenant_id)
            #DEBUG
            self.LOGGER.debug("wslices_dict:1: ")
            self.LOGGER.debug(wslices_dict)

            if wslices_dict["message"]:
                # Either no wnet, or no ap_slices
                self.LOGGER.debug('Appending dictionary message')
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
            self.LOGGER.debug("wslices_dict:2: ")
            self.LOGGER.debug(wslices_dict)

            if wslices_dict["message"]:
                # Either no wnet, or no ap_slices
                self.LOGGER.debug('Appending dictionary message')
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
                self.LOGGER.debug("wslices_dict:3: ")
                self.LOGGER.debug(wslices_dict)

                if wslices_dict["message"]:
                    # Either no wnet, or no ap_slices
                    self.LOGGER.debug('Appending dictionary message')
                    message += wslices_dict["message"]

                else:
                    # Add tags to sql table tenant_tags
                    message += 'Modifying slices in \'' + str(wnet_name) + '\':\n'
                    #TODO: Move to aurora_db
                    try:
                       with mdb.connect(self.mysql_host,
                                        self.mysql_username,
                                        self.mysql_password,
                                        self.mysql_db) as db:
                            for slice_tuple in wslices_dict["ap_slices"]:
                                # For every slice in wnet
                                slice_id = slice_tuple[0]
                                message += '\tslice with ap_slice_id \'' + slice_id + '\'\n'

                                # Add (multiple) tags in MySQL db
                                for tag in args['tag']:
                                    to_execute = "REPLACE INTO tenant_tags VALUES (\'%s\', \'%s\')" \
                                                 % (str(tag), str(slice_id))
                                    self.LOGGER.debug(to_execute)
                                    db.execute(to_execute)

                            # Build rest of message (Not required if efficiency is key)
                            message += 'All slices now include tenant_tag(s) \''
                            message += '\' \''.join(args['tag'])
                            message += '\'.\n'


                    except mdb.Error, e:
                        self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
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
                self.LOGGER.debug("wslices_dict:3: ")
                self.LOGGER.debug(wslices_dict)

                if wslices_dict["message"]:
                    # Either no wnet, or no ap_slices
                    self.LOGGER.debug('Appending dictionary message')
                    message += wslices_dict["message"]

                else:
                    # Add tags to sql table tenant_tags
                    message += 'Modifying slices in \'' + str(wnet_name) + '\':\n'
                    #TODO: Move to aurora_db
                    try:
                       with mdb.connect(self.mysql_host,
                                        self.mysql_username,
                                        self.mysql_password,
                                        self.mysql_db) as db:
                            for slice_tuple in wslices_dict["ap_slices"]:
                                # For every slice in wnet
                                slice_id = slice_tuple[0]

                                # Add (multiple) tags in MySQL db
                                for tag in args['tag']:
                                    to_execute = "SELECT name FROM tenant_tags WHERE ap_slice_id = \'" + \
                                                 str(slice_id) + "\'"
                                    db.execute(to_execute)
                                    names = db.fetchall()
                                    self.LOGGER.debug(names)
                                    if names:
                                        for name in names:
                                            if name[0] == tag:
                                                # This slice has a tag that matches, delete.
                                                to_execute = "DELETE FROM tenant_tags WHERE " + \
                                                             "name = \'%s\' AND ap_slice_id = \'%s\'" \
                                                             % (str(tag), str(slice_id))
                                                self.LOGGER.debug(to_execute)
                                                db.execute(to_execute)
                                                message += '\tslice with ap_slice_id \'' + \
                                                           slice_id + '\'\n'

                            # Build rest of message (Not required if efficiency is key)
                            message += 'All slices no longer include tenant_tag(s) \''
                            message += '\' \''.join(args['tag'])
                            message += '\'.\n'
                    except mdb.Error, e:
                        self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
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
