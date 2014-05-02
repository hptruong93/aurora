# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith &
#              Mike Kobierski 
#
"""The manager module houses the bulk of the logic required to process
commands received from a client.  

"""


import json
import logging
from pprint import pprint, pformat
import prettytable
import sys
import time
import traceback
import uuid
import config

import MySQLdb as mdb

from aurora.aurora_db import *
from aurora import ap_monitor
from aurora import config_db
from aurora.cls_logger import get_cls_logger
from aurora import dispatcher
from aurora.exc import *
from aurora.ap_provision import http_srv as provision_srv
from aurora.request_verification import request_verify_API as Verify
from aurora.request_verification import request_verification as Check
from aurora import slice_plugin


LOGGER = logging.getLogger(__name__)


class Manager(object):
    """High level manager class for handling client requests.

    Every client command has an associated handler in this Manager 
    class.  Each handler is structured to take an argument dictionary,
    as well as tenant_id, project_id, and user_id.  They should all 
    return a dictionary with a boolean 'successful' to notify client 
    if the query was handled without error, as well as a message with 
    additional information.

    """
    #Dispatcher variables

    def __init__(self):
        """Sets up the environment which Manager will use to handle 
        specific tasks.

        Required components include a database handler, message 
        dispatcher (AMQP), and AP Monitor to track access point status
        information.

        Additionally, an HTTP server is set up to provision initial 
        AP configurations.

        """
        self.LOGGER = get_cls_logger(self)
        self.LOGGER.info("Constructing Manager...")

        ### Dispatcher variables
        host = config.CONFIG['dispatcher']['host']
        username = config.CONFIG['dispatcher']['username']
        password = config.CONFIG['dispatcher']['password']
        manager_queue = config.CONFIG['dispatcher']['manager_queue']

        self.mysql_host = config.CONFIG['mysql']['mysql_host']
        self.mysql_username = config.CONFIG['mysql']['mysql_username']
        self.mysql_password = config.CONFIG['mysql']['mysql_password']
        self.mysql_db = config.CONFIG['mysql']['mysql_db']

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
                                              self.aurora_db,
                                              queue=manager_queue)

        self.apm = ap_monitor.APMonitor(self.dispatcher, self.aurora_db, self.mysql_host, self.mysql_username, self.mysql_password)

        provision_srv.run()

    def __del__(self):
        self.LOGGER.info("Destructing Manager...")


    def stop(self):
        """Stops the previously constructed service helpers."""
        self.apm.stop()
        self.dispatcher.stop()
        provision_srv.stop()

    def parseargs(self, function, args, tenant_id, user_id, project_id):
        """Interface to the Manager's handler functions.

        :param str function: Handler function to call
        :param dict args: Generic dictionary passed to function
        :param str tenant_id:
        :param str user_id:
        :param str project_id:
        :rtype: dict

        """

        # args is a generic dictionary passed to all functions (each function is responsible for parsing
        # their own arguments
        function = function.replace('-', '_') #For functions in python
        response = getattr(self, function)(args, tenant_id, user_id, project_id)
        return response

    #Communicate with json file generator
    def configuration_generation(self, args, tenant_id, user_id, project_id):
        #print args['data']
        Message = 'false'
        if 'bridge_type' in args['type'] and ('linux' in args['data'] or 'ovs' in args['data']):
            Message = 'true'
        
        elif 'SSID_NAME' in args['type']:
            Message = 'true'
        
        #print ('VirtualWIFI' in args['data']) and ('wifi_radio' in args['data']['VirtualWIFI'][0]['flavor'])
        elif 'radio_check' in args['type']: # Used to check if the radio configuration is already set
            print "The radio channel exists"
            check = Check.RadioConfigExistedVerification() # check if the radio channel exists
            request = {}

            request['config'] = args['data']['config']
            request['physical_ap'] = args['data']['physical_ap']
            request['tenant_id'] = args['data']['tenant_id']
            error = check.verify('create_slice', request)
            print error
        response = {"status":True, "message":Message}
        return response

    def ap_filter(self, args):
        """A helper method for finding access points based on their 
        SQL entries.  Example argument strings::

            location=mcgill 
            status=UP 
            num_radio_free=1 

        :param str args:
        :rtype: list

        """
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
        """Adds an AP to the SQL database and dispatches a SYN message.

        :rtype: dict

        """
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
                try:
                    self.dispatcher.dispatch({'command':'SYN'}, ap_name)
                except AuroraException as e:
                    message += e.message + '\n'
                    self.LOGGER.warn(e.message)
                except Exception as e:
                    message += e.message + '\n'
                    traceback.print_exc(file=sys.stdout)
                else:
                    message += "%s added" % ap_name
        response = {"status":True, "message":message}
        return response

    def ap_add_tag(self, args, tenant_id, user_id, project_id):
        """Adds a location tag to an access point.

        :rtype: dict

        """
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
            ap_names = []
            args_filter = args['filter'][0]
            ap_list = self.ap_filter(args_filter)
            #Get list of slice_ids
            for entry in ap_list:
                ap_names.append(entry['name'])
        else:
            ap_names = args['ap-add-tag']

        #Add tags
        for ap_name in ap_names:
            for tag in tags:
                message += self.aurora_db.ap_add_tag(ap_name, tag)

        #return response
        response = {"status":True, "message":message}
        return response

    def ap_reset(self, args, tenant_id, user_id, project_id):
        """Resets an access point.

        .. note::

            This results in all the slices on the access point being 
            removed -- they can then be restarted using ap-slice-restart.

        :rtype: dict

        """
        ap_name = args['ap-reset'][0]
        message = "Resetting ap %s" % ap_name
        self.apm.reset_AP(ap_name)
        response = {"status":True, "message":message}
        return response

    def ap_list(self, args, tenant_id, user_id, project_id):
        """Returns a list to the client with nicely printed information 
        about the available access points.

        Some options are available:

        -i   Additional information

        :rtype: dict

        """
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
        """Returns more detailed information about an access point 
        to the client.

        :rtype: dict

        """
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
        """This method will take parameters from the user and modify
        one or more given slices.  The slices can be passed either by
        ap_slice_id or by a filter argument.

        Valid choices for the command line include:

        --interface <tag:endpoint>  Capsulator configuration
        --encrypt <type:key>             Encryption for slice
        --ssid <ap>                      New SSID for slice
        --br <controller>                Bridge controller address

        
        --file <FILE>                    JSON config file

        An abbreviated json with the modifications is generated.  As 
        each section requires a 'name' argument on the agent side, the 
        name of the interface/ssid is found from the configuration 
        database.

        :rtype: dict

        """

        message = ""
        response = {
            "status":False, 
            "message":message,
        }
        config = None
        slices_to_modify = args['ap-slice-modify']
        if args.get('filter') is not None:
                # This will dictate the slices to modify - update 
                # variable slices_to_modify
                # TODO(mike)
                pass
        if len(slices_to_modify) == 0:
            message += "No slices to modify."
        for ap_slice_id in slices_to_modify:
            
            if args.get('file') is not None:
                # Tenant must know what he is doing with the file
                config = args['file']
            else:
                # Build our own config from given arguments, based
                # on previous slice's configuration.
                self.LOGGER.debug("Checking slice ownership...")
                if not self.aurora_db.wslice_belongs_to(tenant_id, 
                                                        project_id, 
                                                        ap_slice_id):
                    message += "You have no slice %s" % ap_slice_id
                    continue

                self.LOGGER.debug("OK!")
                self.LOGGER.debug("Checking if slice deleted...")
                if self.aurora_db.wslice_is_deleted(ap_slice_id):
                    message += "Your slice is deleted: %s" % ap_slice_id
                    continue

                self.LOGGER.debug("OK!")
                try:
                    slice_config = config_db.get_config(ap_slice_id, tenant_id)
                except NoConfigExistsError as e:
                    self.LOGGER.warn(e.message)
                    message += e.message + '\n'
                    continue
                    
                else:
                    config = {}

                    prev_name = None
                    for conf in slice_config.get('RadioInterfaces', []):
                        if conf.get('flavor') == 'wifi_bss':
                            prev_name = conf.get('attributes', {}).get(
                                'name'
                            )

                    new_name = args.get('ssid')
                    if new_name is not None:
                        new_name = new_name[0]
                        config['RadioInterfaces'] = [
                            {
                                "attributes": {
                                    "name":prev_name,
                                    "new_name":new_name,
                                },
                                "flavor":"wifi_bss",
                            },
                        ]

                    encrypt = args.get('encrypt')
                    if encrypt is not None:
                        encrypt = encrypt[0]
                        encryption_type = encrypt.split(':')[0]
                        key = encrypt.split(':')[1]
                        if config.get('RadioInterfaces') is not None:
                            # new SSID already provided, add entry to
                            # attributes
                            if (encryption_type != '' and 
                                    encryption_type is not None):
                                config['RadioInterfaces'][0]['attributes']\
                                    ['encryption_type'] = encryption_type
                            config['RadioInterfaces'][0]['attributes']\
                                ['key'] = key
                        else:
                            if (encryption_type != '' and 
                                    encryption_type is not None):
                                config['RadioInterfaces'] = [
                                    {
                                        "attributes": {
                                            "name":prev_name,
                                            "encryption_type":encryption_type,
                                            "key":key,
                                        },
                                        "flavor":"wifi_bss",
                                    },
                                ]
                            else:
                                config['RadioInterfaces'] = [
                                    {
                                        "attributes": {
                                            "name":prev_name,
                                            "key":key,
                                        },
                                        "flavor":"wifi_bss",
                                    },
                                ]

                    prev_name = None
                    for conf in slice_config.get('VirtualBridges', []):
                        if conf.get('flavor') == 'ovs':
                            prev_name = conf.get('attributes', {}).get(
                                'name'
                            )
                            break

                    controller_addr = args.get('br')
                    if controller_addr is not None:
                        controller_addr = controller_addr[0]
                        config['VirtualBridges'] = [
                            {
                                "attributes": {
                                    "name":prev_name,
                                    "bridge_settings": {
                                        "controller":controller_addr
                                    }
                                },
                                "flavor":"ovs",
                            }
                        ]

                    prev_name = None
                    for conf in slice_config.get('VirtualInterfaces', []):
                        if conf.get('flavor') == 'capsulator':
                            prev_name = conf.get('attributes', {}).get(
                                'name'
                            )
                            break

                    capsulator_config = args.get('interface')
                    if capsulator_config is not None:
                        capsulator_config = capsulator_config[0]
                        tag = capsulator_config.split(':')[0]
                        try:
                            endpoint = capsulator_config.split(':')[1]
                        except IndexError:
                            endpoint = None

                        config['VirtualInterfaces'] = [
                            {
                                "attributes": {
                                    "name":prev_name
                                },
                                "flavor":"capsulator"
                            }
                        ]
                        if tag != '' and tag is not None:
                            config['VirtualInterfaces'][0]['attributes']\
                                    ['tunnel_tag'] = tag
                        if endpoint != '' and endpoint is not None:
                            config['VirtualInterfaces'][0]['attributes']\
                                    ['forward_to'] = endpoint

            # Now we have a config for modify, pass it to agent.
            config_modify = {
                "slice":ap_slice_id, 
                "command":"modify_slice", 
                "user":tenant_id,
                "config":config,
            }
            self.LOGGER.debug(json.dumps(config_modify, indent=4))
            try:
                ap_name = self.aurora_db.get_wslice_physical_ap(ap_slice_id)
            except Exception as e:
                message += e.message + '\n'
                continue
            else:
                try:
                    self.aurora_db.ap_slice_status_pending(ap_slice_id)
                except InvalidStatusUpdate as e:
                    self.LOGGER.warn(e.message)
                try:
                    self.dispatcher.dispatch(config_modify, ap_name)
                except AuroraException as e:
                    message += e.message + '\n'
                    self.LOGGER.warn(e.message)
                except Exception as e:
                    message += e.message + '\n'
                    traceback.print_exc(file=sys.stdout)
                else:
                    message += "Modified %s on %s\n" % (ap_slice_id, ap_name)

        #return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_restart(self, args, tenant_id, user_id, project_id):
        """Restarts a slice on an access point.  

        The configuration should be stored in the JSON configuration 
        database kept by Manager - it is this configuration that is 
        dispatched to the access point.

        :rtype: dict

        """

        slice_names = args['ap-slice-restart'] #Multiple Names
        message = ""
        response = {
            "status":False, 
            "message":message,
        }

        if args['filter']:
            slice_names = []
            args_filter = args['filter'][0]
            slice_list = self.ap_slice_filter(args_filter, tenant_id)
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
                "user":tenant_id,
            }
            error = Verify.verifyOK(tenant_id = tenant_id, request = config_delete)
            if error is not None:
                message += error
                message += "Continuing anyway..."
                #continue

            # Verify slice can be created on new AP
            try:
                config = config_db.get_config(ap_slice_id, tenant_id)
            except NoConfigExistsError as err:
                message += err.message
                continue

            config_restart = {
                "slice":ap_slice_id, 
                "command":"restart_slice", 
                "config":config,
                "user":tenant_id,
            }

            # Passed all checks, restart slice
            self.aurora_db.ap_slice_update_time_stats(ap_slice_id=ap_slice_id)
            try:
                self.aurora_db.ap_slice_status_pending(ap_slice_id)
            except InvalidStatusUpdate as e:
                self.LOGGER.warn(e.message)
            try:
                self.dispatcher.dispatch(config_restart, ap_name)
            except AuroraException as e:
                message += e.message + '\n'
                self.LOGGER.warn(e.message)
            except Exception as e:
                message += e.message + '\n'
                traceback.print_exc(file=sys.stdout)
            else:
                message += "Restarted %s on %s" % (ap_slice_id, ap_name)

        response = {
            "status":True, 
            "message": message,
        }
        return response

    def ap_slice_add_tag(self, args, tenant_id, user_id, project_id):
        """Adds a tag to a slice in the database.

        :rtype: dict

        """
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
            args_filter += "&status!DELETED"
            slice_list = self.ap_slice_filter(args_filter, tenant_id)
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
        """Removes a tag from a slice in the database.

        :rtype: dict

        """
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
            args_filter += "&status!DELETED"
            #TODO: Check this still works with filter
            slice_list = self.ap_slice_filter(args_filter, tenant_id) 

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
        """Configures and dispatches the message required to create 
        a slice on an access point.

        The configuration can be passed to this function by a JSON file,
        which will then be validated using a slice plugin.  The 
        validated configuration will the be stored in a configuration 
        database, in case it is required in the future.

        Some slice data is writen to the SQL database to track its 
        history and associated SSID, owner, and project.

        The ``--hint`` option should give the user some help in choosing 
        a good access point on which he can create his slice.

        :rtype: dict

        """
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
            # arg_tag is not used correctly here, though this is 
            # untested.  Kept in case its omission creates issues.
            # json_list = slice_plugin.SlicePlugin(tenant_id,
            #                         user_id,
            #                         arg_tag).parse_create_slice(arg_file,
            #                                                     len(aplist),
            #                                                     json_list)
            json_list = slice_plugin.SlicePlugin(
                tenant_id,
                user_id
            ).parse_create_slice(
                arg_file,
                len(aplist),
                json_list
            )

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
            error = self.aurora_db.wslice_add(slice_uuid, 
                                              ap_slice_ssid, 
                                              tenant_id, 
                                              aplist[index], 
                                              project_id)
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
            try:
                self.dispatcher.dispatch(json_entry, 
                                         aplist[index], 
                                         str(slice_uuid))
            except AuroraException as e:
                message += e.message + '\n'
                self.LOGGER.warn(e.message)
            except Exception as e:
                message += e.message + '\n'
                traceback.print_exc(file=sys.stdout)
            try:
                config_db.save_config(json_entry['config'], 
                                      json_entry['slice'], 
                                      tenant_id)
            except AuroraException as e:
                LOGGER.error(e.message)

        #Return response (message returns a list of uuids for created slices)
        response = {"status":add_success, "message":message}
        return response

    def ap_slice_delete(self, args, tenant_id, user_id, project_id):
        """Deletes a slice from an access point.

        The associated slice configuration is also removed from the 
        JSON configuration database.  The slice is marked as 'DELETED' 
        in the ap_slice SQL table.

        :rtype: dict

        """
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
            config = {
                "slice":ap_slice_id, 
                "command":"delete_slice", 
                "user":tenant_id
            }

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
            try:
                self.dispatcher.dispatch(config, ap_name)
            except AuroraException as e:
                message += e.message + '\n'
                self.LOGGER.warn(e.message)
            except Exception as e:
                message += e.message + '\n'
                traceback.print_exc(file=sys.stdout)
            try:
                config_db.delete_config(ap_slice_id, tenant_id)
            except AuroraException, e:
                LOGGER.error(e.message)

        #Return response
        response = {"status":True, "message":message}
        return response

    def ap_slice_filter(self, arg_filter, tenant_id):
        """A helper method for finding wireless slices based on their 
        SQL entries.  Example arg_filter strings::

            location=mcgill 
            status=ACTIVE
            ap_slice_ssid=MySSID

        :param str args:
        :param str tenant_id:
        :rtype: list

        """
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

                    if tenant_id == "0" or tenant_id == 0:
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

                    if tenant_id == "0" or tenant_id == 0:
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
                        cur.execute( "SELECT name FROM location_tags WHERE "
                                     "ap_name = '%s'" % tempList[i][3] )
                        tagList = cur.fetchall()
                        for tag in tagList:
                            tagString += str(tag[0])+" "
                        newList[i]['tags'] = tagString
            except mdb.Error, e:
                traceback.print_exc(file=sys.stdout)
                # self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])

        return newList

    def ap_slice_list(self, args, tenant_id, user_id, project_id):
        """Returns a nicely printed table of slices owned by a tenant.

        Some options are available:

        -i    Additional information
        -a    Include deleted slices

        :rtype: dict

        """
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
            "user":tenant_id,
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
            "user":tenant_id, 
            "config":config,
        }
        error = Verify.verifyOK(new_ap, tenant_id, config_create)
        if error is not None:
            response["message"] = error
            return response

        # Passed all checks, delete slice from existing ap and create on new one
        try:
            self.dispatcher.dispatch(config_delete, current_ap)
        except AuroraException as e:
            message += e.message + '\n'
            self.LOGGER.warn(e.message)
        except Exception as e:
            message += e.message + '\n'
            traceback.print_exc(file=sys.stdout)
        try:
            self.dispatcher.dispatch(config_create, new_ap)
        except AuroraException as e:
            message += e.message + '\n'
            self.LOGGER.warn(e.message)
        except Exception as e:
            message += e.message + '\n'
            traceback.print_exc(file=sys.stdout)
        else:
            self.aurora_db.ap_slice_set_physical_ap(ap_slice_id, new_ap)
            self.aurora_db.ap_slice_status_pending(ap_slice_id)
            message += "Moved %s from %s to %s" % (ap_slice_id, current_ap, new_ap)

        response = {
            "status":True, 
            "message": message,
        }
        return response

    def ap_slice_show(self, args, tenant_id, user_id, project_id):
        """Shows more detailed information about a specific slice.

        :rtype: dict

        """
        message = ""
        for arg_id in args['ap-slice-show']:
            if self.aurora_db.wslice_belongs_to(tenant_id, project_id, arg_id):
                message += self.ap_slice_list({'filter':['ap_slice_id=%s' % arg_id,],
                                           'i':True,
                                           'a':True},
                                          tenant_id, user_id, project_id)['message']
            else:
                message += "Error: You have no slice '%s'.\n" % arg_id

        response = {"status":True, "message": message}
        return response

    def ap_slice_sync_config(self, args, tenant_id, user_id, project_id):
        """Queries the access point for a slice and updates the 
        JSON configuration database associated with that slice based 
        on the received data.  

        This ensures that the configuration database and the access 
        point store the same information about slices.

        :rtype: dict

        """
        message = ""
        #TODO:Slice filter integration
        slice_list_to_sync = args['ap-slice-sync-config']

        for ap_slice_id in slice_list_to_sync:

            my_slice = self.aurora_db.wslice_belongs_to(tenant_id, 
                                                        project_id, 
                                                        ap_slice_id)
            if my_slice:
                sync_config = {
                    "slice":ap_slice_id,
                    "command":"sync_config",
                    "user":tenant_id,
                }
                try:
                    physical_ap = self.aurora_db.get_wslice_physical_ap(
                        ap_slice_id
                    )
                except NoSliceExistsException as e:
                    message += e.message + '\n'
                    continue
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    continue
                try:
                    self.dispatcher.dispatch(sync_config, physical_ap)
                except AuroraException as e:
                    message += e.message + '\n'
                    self.LOGGER.warn(e.message)
                except Exception as e:
                    message += e.message + '\n'
                    traceback.print_exc(file=sys.stdout)
                else:
                    message += ("Fetching current configuration from AP: %s" % 
                        ap_slice_id)

        response = {"status":True, "message":message}
        return response

    def wnet_add_wslice(self, args, tenant_id, user_id, project_id):
        """Adds a wireless slice to a wnet.

        :rtype: dict

        """
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
        """Creates a wnet.

        :rtype: dict

        """
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
        """Deletes a wnet.

        :rtype: dict

        """
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
        """Joins a wnet to an existing subnet within SAVI.

        .. warning::

            Not implemented.

        """
        #TODO AFTER SAVI INTEGRATION
        arg_netname = args['wnet-join-subnet'][0]
        arg_wnetname = args['wnet_name'][0]

        #Send to database
        self.LOGGER.warning('NOT YET IMPLEMENTED')

    def wnet_remove_wslice(self, args, tenant_id, user_id, project_id):
        """Removes a wireless slice from a wnet.

        :rtype: dict

        """
        #TODO:Slice filter integration
        message = ""
        arg_name = args['wnet-remove-wslice'][0]
        arg_a = args['all']
        if not args['slice'] and not arg_a:
            err_msg = "No slice specified.\n"
            response = {"status":False, "message":err_msg}
            return response

        slices_to_remove = args.get('slice')
        if arg_a:
            slices_to_remove = []
            wnet_slices_data = self.aurora_db.get_wnet_slices(arg_name, 
                tenant_id
            )
            for ap_slice_data in wnet_slices_data:
                slices_to_remove.append(ap_slice_data.get('ap_slice_id'))


        for arg_slice in slices_to_remove:
            try:
                my_slice = self.aurora_db.wslice_belongs_to(tenant_id, 
                                                            project_id, 
                                                            arg_slice)
                my_wnet = self.aurora_db.wnet_belongs_to(tenant_id, 
                                                         project_id, 
                                                         arg_name)

                if my_slice and my_wnet:
                    if not self.aurora_db.wslice_is_deleted(arg_slice):
                        message += self.aurora_db.wnet_remove_wslice(tenant_id, arg_slice, arg_name)
                    else:
                        message += "Error: Cannot remove deleted slice '%s'" % arg_slice

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
        """Lists the wnets available to tenant.

        Some options are available:

        -i    Show additional information about each wnet

        :rtype: dict

        """
        arg_i = args['i']
        try:
            wnet_to_print = self.aurora_db.get_wnet_list(tenant_id)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            response = {"status":False, "message":e.message}
            return response

        pt = prettytable.PrettyTable()

        try:
            entry = wnet_to_print[0]
        except IndexError as e:
            err_msg = " None"
            response = {"status":True, "message":err_msg}
            return response
        else:
            for attr in entry:
                pt.add_column(attr, [])

        for entry in wnet_to_print:
            table_row = []
            for attr in entry:
                table_row.append(entry[attr])
            pt.add_row(table_row)

        if arg_i:
            message = pt.get_string()
        else:
            message = pt.get_string(fields=["name"])

        response = {"status":True, "message":message}
        return response

    def wnet_show(self, args, tenant_id, user_id, project_id):
        """Shows more detailed information about a wnet.  Also lists 
        the slices associated with the wnet.

        Some options are available:

        -i    Additional information about the associated slices
        -a    Include deleted slices

        :rtype: dict

        """
        arg_i = args['i']
        arg_a = args['all']
        arg_wnet = args['wnet-show'][0]

        try:
            wnet_to_print = self.aurora_db.get_wnet_list(tenant_id, arg_wnet)
            if arg_a:
                slices_to_print = self.aurora_db.get_wnet_slices(
                    arg_wnet, 
                    tenant_id,
                    include_deleted=True
            )
            else:
                slices_to_print = self.aurora_db.get_wnet_slices(
                    arg_wnet, 
                    tenant_id
                )
        except AuroraException as e:
            response = {"status":False, "message":e.message}
            return response
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.LOGGER.error(e)
            response = {"status":False, "message":e.message}
            return response

        pt1 = prettytable.PrettyTable()

        try:
            entry = wnet_to_print[0]
        except IndexError as e:
            err_msg = " None"
            response = {"status":True, "message":err_msg}
            return response
        else:
            for attr in entry:
                pt1.add_column(attr, [])

        for entry in wnet_to_print:
            table_row = []
            for attr in entry:
                table_row.append(entry[attr])
            pt1.add_row(table_row)

        message = pt1.get_string()
        message += '\n\n'

        pt2 = prettytable.PrettyTable()

        try:
            entry = slices_to_print[0]
        except IndexError as e:
            message += " No slices in wnet"
        else:
            for attr in entry:
                pt2.add_column(attr, [])

            for entry in slices_to_print:
                table_row = []
                for attr in entry:
                    table_row.append(entry[attr])
                pt2.add_row(table_row)

            if arg_i:
                message += pt2.get_string()
            else:
                message += pt2.get_string(
                    fields=[
                        "ap_slice_id",
                        "ap_slice_ssid",
                        "physical_ap",
                        "status"
                    ]
                )

        response = {"status":True, "message":message}
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

    def wnet_update_ssid(self, args, tenant_id, user_id, project_id):
        """Updates the SSID of slices within a wnet.  

        SSIDs must be unique on each access point, thus the slices 
        contained within a wnet must all be on different access points.  
        Additionally, no access point may already be hosting an existing 
        slice with the new ssid.

        :rtype: dict

        """

        new_ssid = args['ssid'][0]
        wnet = args['wnet-update-ssid'][0]
        message = ""
        try:
            wnet_slices_data = self.aurora_db.get_wnet_slices(wnet, tenant_id)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            response = {"status":False, "message":e.message}
            return response

        wnet_slices = []
        for slice_data in wnet_slices_data:
            wnet_slices.append(slice_data['ap_slice_id'])

        # SSID's must be unique on an access point
        ap_to_modify = []
        slices_to_modify = []
        for wnet_slice in wnet_slices:
            # Check which access point wnet_slice is on, then verify
            # that no other slices on that access point have the same
            # ssid as new_ssid.  Also verify that, within the wnet,
            # no two slices exist on the same AP.
            try:
                physical_ap = self.aurora_db.get_wslice_physical_ap(wnet_slice)
            except NoSliceExistsException as e:
                message += e.message + '\n'
                continue
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                continue
            if physical_ap in ap_to_modify:
                # Two wnet slices are on the same AP, cannot modify
                message += "Two slices in the wnet are on the same AP\n"
                response = {"status":False, "message":message}
                return response

            ap_to_modify.append(physical_ap)
            for slice_on_ap in self.aurora_db.get_physical_ap_slices(
                    physical_ap, not_deleted_only=True):
                if self.aurora_db.get_wslice_ssid(slice_on_ap) == new_ssid:
                    message += ("Slice on access point already has ssid %s\n" %
                                new_ssid)
                    response = {"status":False, "message":message}
                    return response
            slices_to_modify.append(wnet_slice)


        response = self.ap_slice_modify(
            {
                'ap-slice-modify':slices_to_modify,
                'ssid':[new_ssid,],
            }, 
            tenant_id, 
            user_id, 
            project_id
        )
        returned_message = response['message']
        response['message'] = message + returned_message
        return response

    def wnet_modify_name(self, args, tenant_id, user_id, project_id):
        """Modifies the name given to a specific wnet.

        :rtype: dict

        """
        new_name = args['new_name'][0]
        wnet_id = args['wnet-modify-name'][0]
        message = ""

        my_wnet = self.aurora_db.wnet_belongs_to(tenant_id, 
                                                 project_id, wnet_id)
        
        if not my_wnet:
            message += "Error: You have no wnet '%s'.\n" % wnet_id
            response = {"status":False, "message":message}
            return response

        new_wnet_exists = self.aurora_db.wnet_belongs_to(tenant_id, 
                                                         project_id, new_name)
        if new_wnet_exists:
            message += "Error: You already have a wnet '%s'.\n" % wnet_id
            response = {"status":False, "message":message}
            return response

        self.aurora_db.set_wnet_name(new_name, wnet_id, tenant_id)
        message += "Changed %s to %s\n" % (wnet_id, new_name)
        response = {"status":True, "message":message}
        return response

    def wnet_add_tag(self, args, tenant_id, user_id, project_id):
        """Adds user-defined tags to a wnet.

        :rtype: dict 

        """
        message = ""
        if args['tag'] is None:
            message += "No tags specified.\n"
            response = {"status":False, "message":message}
            return response

        tags = args['tag']

        # Handle more than one wnet
        for wnet_name in args['wnet-add-tag']:
            my_wnet = self.aurora_db.wnet_belongs_to(tenant_id, project_id, 
                                                     wnet_name)
            if not my_wnet:
                message += "Error: You have no wnet '%s'.\n" % wnet_id
                response = {"status":False, "message":message}
                return response

            wnet_slices_data = self.aurora_db.get_wnet_slices(wnet_name, 
                                                              tenant_id)
            wnet_slices = []
            for slice_data in wnet_slices_data:
                wnet_slices.append(slice_data['ap_slice_id'])

            message += "Modifying slices in '%s'\n" % wnet_name
            for ap_slice_id in wnet_slices:
                for tag in tags:
                    message += self.aurora_db.wslice_add_tag(ap_slice_id, tag)

        # Build rest of message (Not required if efficiency is key)
        message += "All slices now include tenant_tag(s) '"
        message += "' '".join(tags)
        message += "'.\n"

        response = {"status":True, "message":message}
        return response

    #Can move some of this functionality to aurora_db
    def wnet_remove_tag(self, args, tenant_id, user_id, project_id):
        """Removes user-defined tags from a wnet.

        :rtype: dict 

        """
        message = ""
        if args['tag'] is None:
            message += "No tags specified.\n"
            response = {"status":False, "message":message}
            return response
        tags = args['tag']

        # Handle more than one wnet
        for wnet_name in args['wnet-remove-tag']:
            my_wnet = self.aurora_db.wnet_belongs_to(tenant_id, project_id, 
                                                     wnet_name)
            if not my_wnet:
                message += "Error: You have no wnet '%s'.\n" % wnet_id
                response = {"status":False, "message":message}
                return response

            wnet_slices_data = self.aurora_db.get_wnet_slices(wnet_name, 
                                                              tenant_id)
            wnet_slices = []
            for slice_data in wnet_slices_data:
                wnet_slices.append(slice_data['ap_slice_id'])
            message += "Modifying slices in '%s'\n" % wnet_name
            for ap_slice_id in wnet_slices:
                for tag in tags:
                    message += self.aurora_db.wslice_remove_tag(ap_slice_id, 
                                                                tag)

        # Build rest of message (Not required if efficiency is key)
        message += "All slices no longer include tenant_tag(s) '"
        message += "' '".join(tags)
        message += "'.\n"

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
