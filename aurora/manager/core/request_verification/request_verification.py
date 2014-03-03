from abc import ABCMeta, abstractmethod

import sys, traceback
sys.path.insert(0,'../ap_provision/')
import ap_provision_reader as provision_reader
import json
import glob
import verification_exception as exceptions
import MySQLdb as mdb

#This module is called by manager before acting on any AP.
#This will detect inconsistency/ invalid request/operation of the manager requested by the client.

GENERAL_CHECK = 'general_check'
CREATE_SLICE = 'create_slice' #This is the command name appears in the request parsed by manager.py
DELETE_SLICE = 'delete_slice' #This is the command name appears in manager.py

#Base abstract class for all verifications
class RequestVerification():
    __metaclass__ = ABCMeta
    
    #This method return a connection to mysql database
    #This method must be wrapped by a try catch block (catching mdb.Error)
    @staticmethod
    def _database_connection():
        return mdb.connect('localhost',
                                   'root',
                                   'supersecret',
                                   'aurora')

    #Get json info file for an ap. Json file is located in manager/core/ap_provision
    @staticmethod
    def _get_physical_ap_info(physical_ap):
        provision_dir = "../ap_provision/"
        for file in glob.glob(provision_dir + "*.json"):
            content = json.load(open(file))
            if content['queue'] == physical_ap:
                return content
        return None

    @staticmethod
    def _ap_name_exists(mysqlCursor, physical_ap):
        mysqlCursor.execute("""SELECT name FROM ap WHERE name = %s""", physical_ap)
        ap_names = mysqlCursor.fetchall()
        if len(ap_names) != 0:
            return True
        return False

    @abstractmethod
    def _verify(self, command, request):
        pass

class APSliceNumberVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_number_of_ap_slice(command, request)
        if check_result:
            raise exceptions.NoAvailableSpaceLeftInAP(check_result)

    #If request = None, it checks for inconsistency in the database, namely an AP with n radios should not have more than 4n ap slices
    #If request != None, it checks for the ap requested for available space.
    #The method raises a NoAvailableSpaceLeftInAP exception if there is any conflict.
    def _check_number_of_ap_slice(self, command, request):
        _ADDITIONAL_SLICE = {#For each command, we will check for a certain adding constant
            GENERAL_CHECK : 0, 
            CREATE_SLICE : 1
        }
        
        try:
            con = RequestVerification._database_connection() 
            with con:
                cursor = con.cursor()

                name = 0
                used_slice = 1
                number_radio = 2

                if request is None:
                    cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
                                      FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
                                            FROM ap_slice 
                                            WHERE status <> "DELETED"
                                              AND status <> "FAILED"
                                            GROUP BY physical_ap) AS 
                                      A LEFT JOIN ap ON A.physical_ap = ap.name
                                      WHERE name IS NOT NULL""")
                    result = cursor.fetchall()
                    
                    for ap in result:
                        if ap[used_slice] > 4 * ap[number_radio]:
                            return 'The AP ' + str(ap[name]) + ' has no space left to create new slice.'
                            #Else return None later
                    #print result #For testing only
                else:
                    if not RequestVerification._ap_name_exists(cursor, request['physical_ap']):
                        raise exceptions.NoSuchAPExists(str(request['physical_ap']))

                    cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
                                      FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
                                            FROM ap_slice 
                                            WHERE status <> "DELETED"
                                              AND status <> "FAILED"
                                            GROUP BY physical_ap) AS 
                                      A LEFT JOIN ap ON A.physical_ap = ap.name
                                      WHERE name = %s """, (request['physical_ap']))
                    result = cursor.fetchall()

                    if len(result) == 0:
                        return None #No slice has been created yet on the interested ap

                    ap = result[0]
                    if ap[used_slice] + _ADDITIONAL_SLICE[command] > 4 * ap[number_radio]: #We create new slice
                        return 'The AP \'' + str(ap[name]) + '\' has no space left to execute command \'' + command + '\'.'
                        #Else return None later

        except mdb.Error, e:
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
        except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
        return None

    
        
#See RadioConfigInvalid exception for what this class is verifying
class RadioConfigExistedVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_radio_config_existed(command, request)
        if check_result:
            raise exceptions.RadioConfigInvalid(check_result)

    # Three methods below are moved to ap_provision_reader...
    # def _get_number_slice_on_radio(self, physical_ap, radio_name):
    #     ap_info = RequestVerification._get_physical_ap_info(physical_ap)
    #     if ap_info is None:
    #         raise exceptions.NoSuchAPExists(str(physical_ap))

    #     #For some reason, the ap_config file stores radio0 information with key "1"??? That is why we have + 1 below
    #     #Below is the number of slices existing on that radio
    #     slices = ap_info['last_known_config']['init_user_id_database']
    #     if str(RequestVerification._get_radio_number(radio_name) + 1) in slices:
    #         return len(slices[str(RequestVerification._get_radio_number(radio_name) + 1)])    
    #     return 0

    #Get the radio that the request is trying to configure
    #KeyError exception should already be caught by caller
    # def _get_radio_configuring(self, radio_interface):
    #     if len(radio_interface) == 0:
    #         return None
    #     else:
    #         for item in radio_interface:
    #             if item['flavor'] == 'wifi_radio':
    #                 return item['attributes']['name']
    #     return None

    #Get the radio that the request is trying to setup the slice on
    #KeyError exception should already be caught by caller
    # def _get_radio_requested(self, radio_interface):
    #     if len(radio_interface) == 0:
    #         return None
    #     else:
    #         for item in radio_interface:
    #             if item['flavor'] == 'wifi_bss':
    #                 return item['attributes']['radio']
    #     return None

    def _check_radio_config_existed(self, command, request):
        if request is None:
            return None
        else:
            #Check for invalid configuration on ap radio using the request
            try:
                request_ap_info = provision_reader.get_physical_ap_info(request['physical_ap'])
                configuring_radio = provision_reader.get_radio_wifi_radio(request['config'])
                request_has_config = configuring_radio is not None

                if configuring_radio is None:
                    requested_radio = provision_reader.get_radio_wifi_bss(request['config']['RadioInterfaces'])
                    number_slices = provision_reader.get_number_slice_on_radio(request_ap_info, requested_radio)
                else:
                    number_slices = provision_reader.get_number_slice_on_radio(request_ap_info, configuring_radio)

                if number_slices == -1:
                    raise exceptions.NoSuchAPExists(str(request['physical_ap']))

                config_existed = number_slices != 0

                if config_existed and request_has_config:
                    return "Radio for the ap " + request['physical_ap'] + " has already been configured. Cannot change the radio's configurations."
                elif (not config_existed) and (not request_has_config):
                    return "Radio for the ap " + request['physical_ap'] + " has not been configured. An initial configuration is required."

            except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
        return None

#See BridgeNumberInvalid exception for what this class is verifying
class BridgeNumberVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_number_of_bridge(command, request)
        if check_result:
            raise exceptions.BridgeNumberInvalid(check_result)

    def _check_number_of_bridge(self, command, request):
        if request is None:
            return None
        else:
            try:
                bridge_list = request['config']['VirtualBridges']
                if len(bridge_list) != 1:
                    return "Attempt to create slice with " + str(len(bridge_list)) + " bridge(s). Exactly one bridge is required."
            except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))

#See VirtualInterfaceNumberInvalid exception for what this class is verifying
class VirtualInterfaceNumberVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_number_of_virtual_interface(command, request)
        if check_result:
            raise exceptions.VirtualInterfaceNumberInvalid(check_result)

    def _check_number_of_virtual_interface(self, command, request):
        try:
            if request is None:
                return None
            else:
                #Check for number of VirtualInterface in the request
                number_of_virtual_interface = len(request['config']['VirtualInterfaces'])
                if number_of_virtual_interface != 2:
                    return "Attempt to create slice with " + str(number_of_virtual_interface) + " interface(s). Exactly two VirtualInterface is required."
            return None
        except KeyError, e:
            raise exceptions.MissingKeyInRequest(str(e.args[0]))
        
#See AccessConflict exception for what this class is verifying
#This class assumes the request has been checked with APSliceNumberVerification, BridgeNumberVerification and
#VirtualInterfaceNumberVerification
class AccessConflictVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_access_conflict(command, request)
        if check_result:
            raise exceptions.AccessConflict(check_result)

    def _check_access_conflict(self, command, request):
        if request is None:
            return None
        else:
            try:
                tenant_id = request['tenant_id']

                requested_bridge = request['config']['VirtualBridges'][0]['attributes']['name']
                requested_interfaces = set([])
                for interface in request['config']['VirtualInterfaces']:
                    requested_interfaces.add(interface['attributes']['attach_to'])

                con = RequestVerification._database_connection()
                with con:
                    cursor = con.cursor()
                    physical_ap = request['physical_ap']                    

                    #Get all of his slices
                    cursor.execute("""SELECT ap_slice_id FROM ap_slice
                                       WHERE tenant_id = %s
                                       AND physical_ap = %s
                                       AND status <> "DELETED"
                                       """, (str(tenant_id), physical_ap))
                    
                    #Get the client's slices
                    result = [item for sublist in cursor.fetchall() for item in sublist]

                    #At this point, we are sure that the ap exists since its existence has been previously checked by
                    #APSliceNumberVerification
                    ap_info = RequestVerification._get_physical_ap_info(physical_ap)
                    init_database = ap_info['last_known_config']['init_database']

                    for slice in init_database:
                        if (slice not in result) and (slice != 'default_slice'): #Then slice must be someone else's
                            current_slice = init_database[slice]
                            bridge = current_slice['VirtualBridges'][0]['attributes']['name']

                            interfaces = set([])
                            for interface in current_slice['VirtualInterfaces']:
                                interfaces.add(interface['attributes']['attach_to'])

                            #Check if conflict
                            if not interfaces.isdisjoint(requested_interfaces):
                                conflict = interfaces.intersection(requested_interfaces)
                                raise exceptions.AccessConflict("Access conflict for interfaces " + ', '.join(conflict))

                            if bridge == requested_bridge:
                                raise exceptions.AccessConflict("Access conflict for bridge. Please choose another bridge.")                                

            except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
            return None

#See IllegalSliceDeletion exception for what this class is verifying
class ValidDeleteVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_slice_delete(command, request)
        if check_result:
            raise exceptions.IllegalSliceDeletion(check_result)

    def _check_slice_delete(self, command, request):
        try:
            if request is None:
                return None
            else:
                #Check for validity of deletion
                con = RequestVerification._database_connection()
                with con:
                    cursor = con.cursor()
                    #Get the ap that the slice is in
                    cursor.execute("""SELECT physical_ap FROM ap_slice
                                       WHERE tenant_id = %s
                                       AND ap_slice_id = %s
                                       AND status <> "DELETED"
                                       """, (str(request['tenant_id']), request['slice'])) #Look for this key in ap_slice_delete in manager.py
                    result = cursor.fetchall()
                    if len(result) == 0:
                        raise exceptions.NoSuchSliceExists(request['slice'])
                    #There should be only one ap_name
                    ap_name = [element for tupl in result for element in tupl][0]

                    ap_name = 'openflow1'
                    ap_info = provision_reader.get_physical_ap_info(ap_name)

                    slice = provision_reader.get_slice(request['slice'], ap_name)

                    current_radio = provision_reader.get_radio_wifi_bss(slice)
                    slice_count = provision_reader.get_number_slice_on_radio(ap_info, current_radio)
                    if slice_count != 1: #Have to check if this is the main slice
                        if provision_reader.get_radio_interface(slice, 'wifi_radio') is not None:
                            return "Cannot delete slice containing radio configurations!"
            return None
        except mdb.Error, e:
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)