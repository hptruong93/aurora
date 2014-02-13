from abc import ABCMeta, abstractmethod

import sys, traceback
sys.path.insert(0,'../ap/')

import json
import os
import glob
import exception
import MySQLdb as mdb

#This module is called by manager before acting on any AP.
#This will detect inconsistency/ invalid request/operation of the manager requested by the client.

GENERAL_CHECK = 'general_check'
CREATE_SLICE = 'create_slice' #This is the command name appears in the request parsed by manager.py

#Base abstract class for all verifications
class RequestVerification():
    __metaclass__ = ABCMeta
    
    #This method return a connection to mysql database
    #This method must be wrapped by a try catch block (catching mdb.Error)
    @staticmethod
    def database_connection():
        return mdb.connect('localhost',
                                   'root',
                                   'supersecret',
                                   'aurora')

    @abstractmethod
    def _verify(self, command, request):
        pass

#Below are the fields that we use to check for inconsistency with the database
#tenant_id
#tennant_tag
#ap_slice_id
#project_id
#physical_ap
#wnet_name
#wnet_id


class APSliceNumberVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_number_of_ap_slice(command, request)
        if check_result:
            raise NoAvailableSpaceLeftInAP(check_result)

    #If request = None, it checks for inconsistency in the database, namely an AP with n radios should not have more than 4n ap slices
    #If request != None, it checks for the ap requested for available space.
    #The method raises a NoAvailableSpaceLeftInAP exception if there is any conflict.
    def _check_number_of_ap_slice(self, command, request):
        _ADDITIONAL_SLICE = {#For each command, we will check for a certain adding constant
            GENERAL_CHECK : 0, 
            CREATE_SLICE : 1
        }
        
        
        try:
            con = RequestVerification.database_connection() 
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
					if not self._ap_name_exists(cursor, request['physical_ap']):
						raise NoSuchAPExists(str(request['physical_ap']))

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
            	raise MissingKeyInRequest(str(e.args[0]))
        return None

    def _ap_name_exists(self, mysqlCursor, physical_ap):
    	mysqlCursor.execute("SELECT name FROM ap")
    	ap_names = mysqlCursor.fetchall()
    	for ap_name in ap_names:
    		if ap_name[0] == physical_ap:
    			return True
    	return False
        
#See RadioConfigInvalid exception for what this class is verifying
class RadioConfigExistedVerification(RequestVerification):
	def _verify(self, command, request):
		check_result = self._check_radio_config_existed(command, request)
		if check_result:
			raise RadioConfigInvalid(check_result)

	def _get_number_slice_on_radio(self, physical_ap, radio_name):
		ap_info = self._get_physical_ap_info(physical_ap)
		if ap_info is None:
			raise NoSuchAPExists(str(physical_ap))

		#For some reason, the ap_config file stores radio0 information with key "1"??? That is why we have + 1 below
		#Below is the number of slices existing on that radio
		slices = ap_info['last_known_config']['init_user_id_database']
		if str(self._get_radio_number(radio_name) + 1) in slices:
			return len(slices[str(self._get_radio_number(radio_name) + 1)])    
		return 0

    #Get the radio that the request is trying to configure
    #KeyError exception should already be caught by caller
	def _get_radio_configuring(self, radio_interface):
		if len(radio_interface) == 0:
			return None
		else:
			for item in radio_interface:
				if item['flavor'] == 'wifi_radio':
					return item['attributes']['name']
		return None

    #Get the radio that the request is trying to setup the slice on
    #KeyError exception should already be caught by caller
	def _get_radio_requested(self, radio_interface):
		if len(radio_interface) == 0:
			return None
		else:
			for item in radio_interface:
				if item['flavor'] == 'wifi_bss':
					return item['attributes']['radio']
		return None

	#Get json info file for an ap. Json file is located in manager/provision_server
	def _get_physical_ap_info(self, physical_ap):
		os.chdir("./provision_server")
		for file in glob.glob("*.json"):
			content = json.load(open(file))
			if content['queue'] == physical_ap:
				return content
		return None

	#Radio name: radio0, radio1, ... radio10, 
	def _get_radio_number(self, radio_name):
		return int(radio_name[len('radio')])

	def _check_radio_config_existed(self, command, request):
		if request is None:
			return None
		else:
            #Check for invalid configuration on ap radio using the request
			try:
				configuring_radio = self._get_radio_configuring(request['config']['RadioInterfaces'])
				request_has_config = configuring_radio is not None

				if configuring_radio is None:
					requested_radio = self._get_radio_requested(request['config']['RadioInterfaces'])
					number_slices = self._get_number_slice_on_radio(request['physical_ap'], requested_radio)
				else:
					number_slices = self._get_number_slice_on_radio(request['physical_ap'], configuring_radio)

				config_existed = number_slices != 0

				if config_existed and request_has_config:
					return "Radio for the ap " + request['physical_ap'] + " has already been configured. Cannot change the radio's configurations."
				elif (not config_existed) and (not request_has_config):
					return "Radio for the ap " + request['physical_ap'] + " has not been configured. An initial configuration is required."

			except KeyError, e:
				raise MissingKeyInRequest(str(e.args[0]))
		return None

class VirtualInterfaceVerification(RequestVerification):
    def _verify(self, command, request):
        check_result = self._check_number_of_virtual_interface(command, request)
        if check_result:
            raise VirtualInterfaceNumberInvalid(check_result)

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
            return 'Key \'' + str(e.args[0]) + '\' could not be found. Please check request'
        
#Base abstract class for all exception raised (when conflict detected)
class VerificationException(exception.AuroraException):
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def _handle_exception(self):
        #Tell the client about the problem here or resolve internally
        pass

#This exception is raised when the verifier cannot find the ap mentioned in the request, either in the database or the
#provision folder of manager
class NoSuchAPExists(VerificationException):
	def __init__(self, message = "not_provided"):
		self.message = message
		super(NoSuchAPExists, self).__init__(message)
    
	def _handle_exception(self):
		return "Cannot find any AP named \'" + self.message + "\'"

class MissingKeyInRequest(VerificationException):
	def __init__(self, message = "not_provided"):
		self.message = message
		super(MissingKeyInRequest, self).__init__(message)
    
	def _handle_exception(self):
		return 'Key \'' + self.message + '\' could not be found. Please check request!'

#This exception is raised when an AP is having, or is requested to have more than 4n ap slices with n is the AP's number of radios
class NoAvailableSpaceLeftInAP(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(NoAvailableSpaceLeftInAP, self).__init__(message)
    
    def _handle_exception(self):
        return self.message

#This exception is raised when the client attempts to configure the radio when it is already configured, or the client
# attempts to create new slice on a radio that has not been configured yet without any intial configurations.
class RadioConfigInvalid(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(RadioConfigInvalid, self).__init__(message)

    def _handle_exception(self):
        return self.message

#This exception is raised when the client attempts to create a new slice and provide an invalid number of VirtualInterface
#The number of VirtualInterfaces expected is two.
class VirtualInterfaceNumberInvalid(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(VirtualInterfaceNumberInvalid, self).__init__(message)

    def _handle_exception(self):
        return self.message    


class RequestVerifier():
    #The command names must be identical to the method calling
    #verification from aurora_db.py
    _commands = {
        GENERAL_CHECK : [APSliceNumberVerification()],
        CREATE_SLICE : [APSliceNumberVerification(), 
                        RadioConfigExistedVerification(),
                        VirtualInterfaceVerification()]
    }

    #If there is any problem with the verification process, the function will return
    #a string with error information for client to take further actions.
    #If everything is OK, the function return None
    @staticmethod
    def isVerifyOK(command, request):
        for verifier in RequestVerifier._commands[command]:
            try:
                verifier._verify(command, request)
            except VerificationException as ex:
                #print ex._handle_exception() #Testing only
                return ex._handle_exception()
            except Exception:
            	traceback.print_exc(file=sys.stdout)
            	sys.exit(1)
        return None


#Use this method as an interface for the verification. Internal structure above must not be accessed from outside of the file
def verifyOK(request = None):
    if request is None:
        command = GENERAL_CHECK
    else:
        command = request['command']
    return RequestVerifier.isVerifyOK(command, request)

if __name__ == '__main__':
    #Testing
    request = {
    "command": "create_slice", 
    "config": {
        "RadioInterfaces": [
            {
                "attributes": {
                    "channel": "1", 
                    "country": "CA", 
                    "disabled": "0", 
                    "hwmode": "abg", 
                    "name": "radio0", 
                    "txpower": "20"
                }, 
                "flavor": "wifi_radio"
            },
            {
                "attributes": {
                    "encryption_type": "wep-open", 
                    "if_name": "wlan0", 
                    "key": "12345", 
                    "name": "MK", 
                    "radio": "radio0"
                }, 
                "flavor": "wifi_bss"
            }
        ], 
        "VirtualBridges": [
            {
                "attributes": {
                    "bridge_settings": {}, 
                    "interfaces": [
                        "vwlan0", 
                        "veth0"
                    ], 
                    "name": "linux-br", 
                    "port_settings": {}
                }, 
                "flavor": "linux_bridge"
            }
        ], 
        "VirtualInterfaces": [
            {
                "attributes": {
                    "attach_to": "wlan0", 
                    "name": "vwlan0"
                }, 
                "flavor": "veth"
            },
            {
                "attributes": {
                    "attach_to": "eth0", 
                    "name": "veth0"
                }, 
                "flavor": "veth"
            }, 
            
        ]
    }, 
    "physical_ap": "openflow1",
    "slice": "null", 
    "user": 1
}
    print RequestVerifier.isVerifyOK('create_slice', request)
#     isVerifyOK(CREATE_SLICE, {
#     "command": "create_slice", 
#     "config": {
#         "RadioInterfaces": [
#             {
#                 "attributes": {
#                     "channel": "1", 
#                     "country": "CA", 
#                     "disabled": "0", 
#                     "hwmode": "abg", 
#                     "name": "radio0", 
#                     "txpower": "20"
#                 }, 
#                 "flavor": "wifi_radio"
#             }, 
#             {
#                 "attributes": {
#                     "encryption_type": "wep-open", 
#                     "if_name": "wlan0", 
#                     "key": "12345", 
#                     "name": "MK", 
#                     "radio": "radio0"
#                 }, 
#                 "flavor": "wifi_bss"
#             }
#         ], 
#         "VirtualBridges": [
#             {
#                 "attributes": {
#                     "bridge_settings": {}, 
#                     "interfaces": [
#                         "vwlan0", 
#                         "veth0"
#                     ], 
#                     "name": "linux-br", 
#                     "port_settings": {}
#                 }, 
#                 "flavor": "linux_bridge"
#             }
#         ], 
#         "VirtualInterfaces": [
#             {
#                 "attributes": {
#                     "attach_to": "eth0", 
#                     "name": "veth0"
#                 }, 
#                 "flavor": "veth"
#             }, 
#             {
#                 "attributes": {
#                     "attach_to": "wlan0", 
#                     "name": "vwlan0"
#                 }, 
#                 "flavor": "veth"
#             }
#         ]
#     }, 
#     "physical_ap": "openflow"
#     "slice": null, 
#     "user": 1
# })