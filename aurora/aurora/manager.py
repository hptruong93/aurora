# Aurora Manager Functions
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json
import logging
from pprint import pprint, pformat
import prettytable
import sys
import time
import traceback
import uuid

import MySQLdb as mdb

from aurora.aurora_db import *
from aurora import ap_monitor
from aurora import config_db
from aurora.cls_logger import get_cls_logger
from aurora import dispatcher
from aurora.exc import *
from aurora.ap_provision import http_srv as provision_srv
from aurora.request_verification import request_verify_API as Verify
from aurora import slice_plugin

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
        self.aurora_db = AuroraDB(self.mysql_host,
                                 self.mysql_username,
                                 self.mysql_password,
                                 self.mysql_db)
        #Comment for testing without AP
        self.dispatcher = dispatcher.Dispatcher(host,
                                              username,
                                              password,
                                              self.mysql_username,
                                              self.mysql_password,
                                              self.aurora_db)

        self.apm = ap_monitor.APMonitor(self.dispatcher, self.aurora_db, self.mysql_host, self.mysql_username, self.mysql_password)

        provision_srv.run()

    def __del__(self):
        self.LOGGER.info("Destructing Manager...")


    def stop(self):
        self.apm.stop()
        self.dispatcher.stop()
        provision_srv.stop()

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
            # self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
            # sys.exit(1)
            traceback.print_exc(file=sys.stdout)

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
                traceback.print_exc(file=sys.stdout)
                # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
        else: #Multiple arguments (name=openflow & firmware=openwrt & region=mcgill & number_radio>1)
            tag_compare = False #For tags, we need 2 queries and a quick result compare at the end
            tag_result = []
            args_list = args.split('&')
            
            if args_list[0] == 'location' or args_list[0] == 'location,slice-load':  # Yang: add one more case if the user ask for the location_tag ['location']
                try:
                    with self.con:
                        cur = self.con.cursor()
                        tempList = []
                        if 'location' in args_list[0]:
                            cur.execute("SELECT * FROM location_tags")
                            tempList = list(cur.fetchall())
                            return tempList
                except mdb.Error, e:
                    print "Error %d: %s" % (e.args[0], e.args[1])

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
                        traceback.print_exc(file=sys.stdout)
                        # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])

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
                traceback.print_exc(file=sys.stdout)
                # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])

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

    def ap_add(self, args, tenant_id, user_id, project_id):
        message = ""
        for ap_name in args['ap-add']:
            self.LOGGER.info("Adding ap %s", ap_name)
            response = {"status":False, "message":None}
            try:
                self.aurora_db.ap_add(ap_name)
            except Exception as e:
                self.LOGGER.warn(e)
                message += e.message
            else:
                self.dispatcher.dispatch({'command':'SYN'}, ap_name)
                message += "%s added" % ap_name
        response = {"status":True, "message":message}
        return response

    def ap_reset(self, args, tenant_id, user_id, project_id):
        ap_name = args['ap-reset'][0]
        message = "Resetting ap %s" % ap_name
        self.apm.reset_AP(ap_name)
        response = {"status":True, "message":message}
        return response

    def ap_list(self, args, tenant_id, user_id, project_id):
        #TODO: Verify filter passes correctly
        if args['filter']:
            arg_filter = args['filter'][0]
        else:
            arg_filter = []
        arg_i = args['i']
        toPrint = self.ap_filter(arg_filter)
        message = ""

        pt = prettytable.PrettyTable()

        # Populate column headings
        try:
            entry = toPrint[0]
        except IndexError as e:
            # There are no access points to list
            err_msg = " None"
            response = {"status":True, "message":err_msg}
            return response

        else:
            pt.add_column("Name", [])
            for attr in entry[1]:
                pt.add_column(attr, []) 

        # Populate table rows
        for entry in toPrint:
            table_row = []
            table_row.append(entry[0])
            for attr in entry[1]:
                table_row.append(entry[1][attr])
            pt.add_row(table_row)
        if arg_i:
            message = pt.get_string()
        else:
            message = pt.get_string(fields=["Name", "status"])    

        #return response
        response = {"status":True, "message":message}
        return response

    def ap_show(self, args, tenant_id, user_id, project_id):
        #TODO: Verify filter passes correctly
        arg_name = args['ap-show'][0]
        toPrint = self.ap_filter('name='+arg_name)
        message = ""

        message += self.ap_list(
                {
                    'filter':['name=%s' % arg_name,],
                    'i':True
                },
                tenant_id, 
                user_id, 
                project_id
        )['message']

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
        message = ""
        response = {
            "status":False, 
            "message":message,
        }

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
                ap_name = self.aurora_db.get_wslice_physical_ap(ap_slice_id)
            except Exception as e:
                message += e.message
                continue

            if not self.aurora_db.wslice_belongs_to(tenant_id, project_id, ap_slice_id):
                message += "You have no slice %s" % ap_slice_id
                continue

            if self.aurora_db.wslice_is_deleted(ap_slice_id):
                message += "Your slice is deleted, cannot restart: %s" % ap_slice_id
                continue

            # Verify slice can be deleted from current AP
            config_delete = {
                "slice":ap_slice_id, 
                "command":"delete_slice", 
                "user":user_id,
            }
            error = Verify.verifyOK(tenant_id = tenant_id, request = config_delete)
            if error is not None:
                message += error
                continue

            # Verify slice can be created on new AP
            try:
                config = config_db.get_config(ap_slice_id, tenant_id)
            except NoConfigExistsError as err:
                message += err.message
                continue

            config_create = {
                "slice":ap_slice_id, 
                "command":"create_slice", 
                "user":user_id, 
                "config":config,
            }

            # Passed all checks, delete slice from existing ap and create on new one
            self.dispatcher.dispatch(config_delete, ap_name)
            self.aurora_db.ap_slice_status_pending(ap_slice_id)
            self.dispatcher.dispatch(config_create, ap_name)
            message += "Restarted %s on %s" % (ap_slice_id, ap_name)

        response = {
            "status":True, 
            "message": message,
        }
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
            if self.aurora_db.wslice_belongs_to(tenant_id, project_id, slice_id):
                for tag in tags:
                    message += self.aurora_db.wslice_add_tag(slice_id, tag)
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
            if self.aurora_db.wslice_belongs_to(tenant_id, project_id, slice_id):
                for tag in tags:
                    message += self.aurora_db.wslice_remove_tag(slice_id, tag)
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
        arg_hint = None
        if 'ap' in args:
            arg_ap = args['ap']
        if args['filter']:
            arg_filter = args['filter'][0]
        if 'file' in args:
            arg_file = args['file']
        if args['tag']:
            arg_tag = args['tag'][0]
        if args['hint']:
            arg_hint = args['hint'][0]

        json_list = [] # If a file is provided for multiple APs,
                       # we need to split the file for each AP, saved here
        # Add one section for dealing with 'hint' token, once it is processed, return
        if arg_hint:
            if "location" in arg_hint:
                # Try to access the local database to grab location
                tempList = self.ap_filter(arg_hint)
                message = ""
                for entry in tempList:
                    if not ('mcgill' in entry[0] or 'mcgill' in entry[1]):
                        message += "%5s: %s\n" % (entry[1], entry[0])
                


                # Make a decision according to the token "location" OR "slice_load"
                try:
                    if args.get('location') is not None: # if there is a location specification
                        if args['location'].lower() in message.lower(): # check if the location is valid
                            indexSliceLoad = ""
                            freespace = 0;
                            if "slice-load" in arg_hint:
                                print "Search the lightweight AP"
                                indexSliceLoad = "unknown"
                            else:
                                print "Locate a random AP"
                            
                            # Search for the proper slices
                            for entry in tempList:
                                if args['location'].lower() == entry[0].lower():
                                    # once the location matches -- check if the AP has free spots
                                    apList = self.ap_filter("name=" + entry[1])

                                    if apList[0][1]['number_slice_free'] > 0:
                                        if(len(indexSliceLoad)==0):
                                            indexSliceLoad = entry[1]
                                            break
                                        elif(apList[0][1]['number_slice_free']>freespace):
                                            freespace = apList[0][1]['number_slice_free']
                                            indexSliceLoad = entry[1]

                            message = indexSliceLoad
                        else:
                            message = "invalid location information"
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    print "This is the first term"
                    
                response = {"status":True, "message":message}
                return response
            if arg_file is None:
                raise NoSliceConfigFileException()

        # end of the section

        if arg_ap:
            aplist = arg_ap
        elif arg_filter: # We need to apply the filter
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
            arg_file['TrafficAttributes'] = []

        # Initialize json_list structure (We do NOT yet have a plugin for
        # VirtualWIFI/RadioInterfaces, just load and send for now)
        for i in range(len(aplist)):
            json_list.append({'VirtualInterfaces':[],
                              'VirtualBridges':[],
                              'RadioInterfaces':arg_file['VirtualWIFI'],
                              'TrafficAttributes':arg_file['TrafficAttributes']})

        # Send to plugin for parsing
        try:
            json_list = slice_plugin.SlicePlugin(tenant_id,
                                    user_id,
                                    arg_tag).parse_create_slice(arg_file,
                                                                len(aplist),
                                                                json_list)

        except Exception as e:
            self.LOGGER.error(e.message)
            response = {"status":False, "message":e.message}
            traceback.print_exc(file=sys.stdout)
            return response

        # Print json_list (for debugging)
        for i, entry in enumerate(json_list):
            self.LOGGER.debug(json.dumps(entry, indent=4))

        add_success = True
        # Dispatch
        for (index,json_entry) in enumerate(json_list):
            # Generate unique slice_id and add entry to database
            slice_uuid = uuid.uuid4()
            json_entry['slice'] = str(slice_uuid)
            
            # Verify adding process. See request_verification for more information
            # An error message is retuned if there is any problem, else None is returned.
            error = Verify.verifyOK(aplist[index], tenant_id, json_entry)
            if error is not None: 
                message += error + "\n"
                add_success = False
                continue

            # There is no error
            # Get SSID of slice to be created, only first is captured
            ap_slice_ssid = None
            for d_entry in json_entry['config']['RadioInterfaces']:
                if d_entry['flavor'] == 'wifi_bss':
                    ap_slice_ssid = d_entry['attributes']['name']
                    break

            # Add slice to MySQL DB
            error = self.aurora_db.wslice_add(slice_uuid, ap_slice_ssid, tenant_id, aplist[index], project_id)
            if error is not None: #There is an error
                message += error + "\n"
                add_success = False
                self.aurora_db.wslice_delete(slice_uuid)
                continue

            message += "Adding slice %s: %s\n" % (index + 1, slice_uuid)

            #Add tags if present
            if args['tag']:
                self.ap_slice_add_tag({'ap-slice-add-tag':[slice_uuid],
                                'tag': [arg_tag],
                                'filter':""},
                                tenant_id, user_id, project_id)

            #Dispatch (use slice_uuid as a message identifier)
            self.dispatcher.dispatch(json_entry, aplist[index], str(slice_uuid))
            try:
                config_db.save_config(json_entry['config'], json_entry['slice'], tenant_id)
            except AuroraException, e:
                LOGGER.error(e.message)

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

      #  self.LOGGER.debug("ap_slice_list: %s",ap_slice_list)

        if not ap_slice_list:
            message += " None to delete\n"

        for ap_slice_id in ap_slice_list:
            config = {"slice":ap_slice_id, "command":"delete_slice", "user":user_id}

            my_slice = self.aurora_db.wslice_belongs_to(tenant_id, project_id, ap_slice_id)
            if not my_slice:
                message += "No slice '%s'\n" % ap_slice_id
                if ap_slice_id == ap_slice_list[-1]:
                    response = {"status":False, "message":message}
                    return response #Should continue here instead of returning so soon???
                else:
                    continue

            error = Verify.verifyOK(tenant_id = tenant_id, request = config)
            if error is not None:
                message += error + '\n'
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
                    ap_name = self.aurora_db.get_wslice_physical_ap(ap_slice_id)
            except Exception as e:
                response = {"status":False, "message":message + e.message}
                traceback.print_exc(file=sys.stdout)
                return response
            message += self.aurora_db.wslice_delete(ap_slice_id)

            #Dispatch
            #Generate unique message id
            self.LOGGER.debug("Launching dispatcher")
            self.dispatcher.dispatch(config, ap_name)
            try:
                config_db.delete_config(ap_slice_id, tenant_id)
            except AuroraException, e:
                LOGGER.error(e.message)

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
            traceback.print_exc(file=sys.stdout)
            # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            # sys.exit(1)
        newList = [] #Result list
        if len(arg_filter) == 0: #No filter or tags
            try:
                with self.con:
                    cur = self.con.cursor()

                    if tenant_id == 0:
                        to_execute = """SELECT * 
                            FROM 
                                (SELECT ap_slice_id, total_mb_sent, total_active_duration
                                    FROM
                                        metering
                                ) AS A
                                RIGHT JOIN ap_slice AS B USING (ap_slice_id)"""
                        self.LOGGER.debug(to_execute)
                        cur.execute(to_execute)
                    else:
                        to_execute = """SELECT * 
                            FROM 
                                (SELECT ap_slice_id, total_mb_sent, total_active_duration
                                    FROM
                                        metering
                                ) AS A
                                RIGHT JOIN ap_slice AS B USING (ap_slice_id)
                            WHERE 
                                tenant_id = '%s'""" % tenant_id
                        self.LOGGER.debug(to_execute)
                        cur.execute(to_execute)




                    # if tenant_id == 0:
                    #     cur.execute("SELECT * FROM ap_slice")
                    # else:
                    #     cur.execute( "SELECT * FROM ap_slice WHERE "
                    #                  "tenant_id = '%s'" % tenant_id )
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
                        newList[i]['total_mb_sent'] = tempList[i][7]
                        newList[i]['total_active_duration'] = tempList[i][8]
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
                traceback.print_exc(file=sys.stdout)
                # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
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
                                    self.LOGGER.debug("Looking for location info: %s", location)
                                    if tenant_id == 0:
                                        cur.execute( "SELECT ap_slice_id FROM ap_slice WHERE "
                                                     "physical_ap = '%s'" % location[0] )
                                    else:
                                        cur.execute( "SELECT ap_slice_id FROM ap_slice WHERE "
                                                     "tenant_id = '%s' AND "
                                                     "physical_ap = '%s'" % (tenant_id, location[0]) )
                                    phys_ap = cur.fetchall()
                                    self.LOGGER.debug("phys_ap: %s", phys_ap)
                                    for result in phys_ap:
                                        if result[0] not in tag_result:
                                            tag_result.append(result[0])
                            else:
                                raise Exception("Unexpected character in tag query. "
                                                "Please check syntax and try again!")


                    except mdb.Error, e:
                        traceback.print_exc(file=sys.stdout)
                        # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])

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
            self.LOGGER.debug("SQL Filter: %s", expression)

            #Execute Query
            try:
                with self.con:
                    cur = self.con.cursor()
                    #TODO: Allow admin to see all (tenant_id of 0)
                    if len(expression) == 0:
                        expression = ''

                    if tenant_id == 0:
                        cur.execute( ("""SELECT * 
                            FROM 
                                (SELECT ap_slice_id, total_mb_sent, total_active_duration
                                    FROM
                                        metering
                                ) AS A
                                RIGHT JOIN ap_slice AS B USING (ap_slice_id)
                            WHERE """
                        ) + expression) 
                    else:
                        cur.execute( ("""SELECT * 
                            FROM 
                                (SELECT ap_slice_id, total_mb_sent, total_active_duration
                                    FROM
                                        metering
                                ) AS A
                                RIGHT JOIN ap_slice AS B USING (ap_slice_id)
                            WHERE 
                                tenant_id = '%s' AND """ % tenant_id
                        ) + expression)
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
                        # TODO: Append these values from metering table
                        newList[i]['total_mb_sent'] = tempList[i][7]
                        newList[i]['total_active_duration'] = tempList[i][8]
                        #Get a list of tags
                        cur.execute("SELECT name FROM tenant_tags WHERE ap_slice_id='%s'" % tempList[i][0])
                        tagList = cur.fetchall()
                        tagString = ""
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i]['tags'] = tagString

            except mdb.Error, e:
                traceback.print_exc(file=sys.stdout)
                # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])

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
        self.LOGGER.debug("arg_filter: %s", arg_filter)

        try:
            newList = self.ap_slice_filter(arg_filter, tenant_id)
        except Exception as e:
            message += e.message
            self.LOGGER.error(e)
            traceback.print_exc(file=sys.stdout)
            response = {"status":False, "message":message}
            return response
        if not newList:
            message += " None\n"
        else:
            pt = prettytable.PrettyTable()
            entry = newList[0]
            for attr in entry:
                pt.add_column(attr, [])
                
            # Populate table rows
            for entry in newList:
                table_row = []
                for attr in entry:
                    table_row.append(entry[attr])
                pt.add_row(table_row)
            if arg_i:
                message = pt.get_string()
            else:
                message = pt.get_string(fields=["ap_slice_id", "ap_slice_ssid", "physical_ap", "status"])

        #Return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_move(self, args, tenant_id, user_id, project_id):
        """Moves a slice from once access point to another.

        The configuration for the slice must not be given,
        and will be fetched from the configuration database
        by slice ID and tenant ID.  No special handover
        methods are implemented, and all wireless clients
        connected to the slice will have to reassociate with 
        the new access point.

        :param dict args:
        :param int tenant_id:
        :rtype: dict

        """
        message = ""
        response = {
            "status":False, 
            "message":message,
        }
        new_ap = args['ap'][0]
        ap_slice_id = args['ap-slice-move'][0]
        if not self.aurora_db.wslice_belongs_to(tenant_id, project_id, ap_slice_id):
            message = "You have no slice %s" % ap_slice_id
            response["message"] = message
            return response

        if self.aurora_db.wslice_is_deleted(ap_slice_id):
            message = "Your slice is deleted: %s" % ap_slice_id
            response["message"] = message
            return response

        # Verify slice can be deleted from current AP
        config_delete = {
            "slice":ap_slice_id, 
            "command":"delete_slice", 
            "user":user_id,
        }
        error = Verify.verifyOK(tenant_id = tenant_id, request = config_delete)
        if error is not None:
            response["message"] = error
            return response

        # Verify slice can be created on new AP
        current_ap = self.aurora_db.get_wslice_physical_ap(ap_slice_id)
        try:
            config = config_db.get_config(ap_slice_id, tenant_id)
        except NoConfigExistsError as err:
            response["message"] = err.message
            return response

        config_create = {
            "slice":ap_slice_id, 
            "command":"create_slice", 
            "user":user_id, 
            "config":config,
        }
        error = Verify.verifyOK(new_ap, tenant_id, config_create)
        if error is not None:
            response["message"] = error
            return response

        # Passed all checks, delete slice from existing ap and create on new one
        self.dispatcher.dispatch(config_delete, current_ap)
        self.dispatcher.dispatch(config_create, new_ap)
        self.aurora_db.ap_slice_set_physical_ap(ap_slice_id, new_ap)
        self.aurora_db.ap_slice_status_pending(ap_slice_id)
        message += "Moved %s from %s to %s" % (ap_slice_id, current_ap, new_ap)

        response = {
            "status":True, 
            "message": message,
        }
        return response

    def ap_slice_show(self, args, tenant_id, user_id, project_id):
        message = ""
        for arg_id in args['ap-slice-show']:
            if self.aurora_db.wslice_belongs_to(tenant_id, project_id, arg_id):
                message += self.ap_slice_list({'filter':['ap_slice_id=%s' % arg_id,],
                                           'i':True,
                                           'a':True},
                                          tenant_id, user_id, project_id)['message']
            else:
                message += "Error: You have no slice '%s'.\n" % arg_id
            #if arg_id == args['ap-slice-show'][-1]:
            #   response = {"status":False, "message": message}
            #  return response

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

            self.LOGGER.debug("arg_name: %s", arg_name)
            self.LOGGER.debug("arg_slice: %s", arg_slice)

            my_slice = self.aurora_db.wslice_belongs_to(tenant_id, project_id, arg_slice)
            my_wnet = self.aurora_db.wnet_belongs_to(tenant_id, project_id, arg_name)

            #Send to database
            if my_slice and my_wnet:
                if not self.aurora_db.wslice_is_deleted(arg_slice):
                    message += self.aurora_db.wnet_add_wslice(tenant_id, arg_slice, arg_name)
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
        message += self.aurora_db.wnet_add(arg_uuid, arg_name, tenant_id, project_id)

        #Send Response
        response = {"status":True, "message":message}
        return response

    def wnet_delete(self, args, tenant_id, user_id, project_id):
        arg_name = args['wnet-delete'][0]

        #Send to database
        try:
            message = self.aurora_db.wnet_remove(arg_name, tenant_id)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
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
                my_slice = self.aurora_db.wslice_belongs_to(tenant_id, project_id, arg_slice)
                my_wnet = self.aurora_db.wnet_belongs_to(tenant_id, project_id, arg_name)

                if my_slice and my_wnet:
                    if not self.aurora_db.wslice_is_deleted(arg_slice):
                        message += self.aurora_db.wnet_remove_wslice(tenant_id, arg_slice, arg_name)
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
                traceback.print_exc(file=sys.stdout)
                response = {"status":False, "message":e.message}
                return response

            #Send to database
          #  message += self.aurora_db.wnet_remove_wslice(tenant_id, arg_slice, arg_name)
          #  message = "Slice '%s' removed from '%s'.\n" % (arg_slice, arg_name)

        #Send Response
        response = {"status":True, "message":message}
        return response

    def wnet_list(self, args, tenant_id, user_id, project_id):
        """Lists the wnets available to tenant"""
        arg_i = args['i']
        try:
            wnet_to_print = self.aurora_db.get_wnet_list(tenant_id)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
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
            wnet_to_print = self.aurora_db.get_wnet_list(tenant_id, arg_wnet)

            slices_to_print = self.aurora_db.get_wnet_slices(arg_wnet, tenant_id)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
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

        Returns a dictionary containing::
        
            {   "message":<NoneType if successful, something
                             if wnet doesn't exist>
                "ap_slices":<NoneType if none, otherwise::
                              a tuple of tuples with ap_slice
                              info related to specified wnet_name>
            }

        """
        return_dictionary = {}
        #DEBUG
        self.LOGGER.debug("wnet_name: %s", wnet_name)

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
                    self.LOGGER.debug("wnet_id: %s" + str(wnet_id))

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
            traceback.print_exc(file=sys.stdout)
            # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            # sys.exit(1)

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
                    self.aurora_db.wnet_remove_slice(tenant_id, slice_id, wnet_name)
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
                        traceback.print_exc(file=sys.stdout)
                        # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
                        # sys.exit(1)
        response = {"status":True, "message":message}
        return response

    #Can move some of this functionality to aurora_db
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
                        traceback.print_exc(file=sys.stdout)
                        # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
                        # sys.exit(1)
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
