from abc import ABCMeta, abstractmethod

import sys
sys.path.insert(0,'../ap/')

import exception
import MySQLdb as mdb
import manager

#This module is called by manager before acting on any AP.
#This will detect inconsistency/ invalid request/operation of the manager requested by the client.

GENERAL_CHECK = 'general_check'
CREATE_SLICE = 'create_slice' #This is the command name appears in the request parsed by manger.py

#Base abstract class for all verifications
class RequestVerification():
	__metaclass__ = ABCMeta
	
	#This method return a connection to mysql database
	#This method must be wrapped by a try catch block (catching mdb.Error)
	@staticmethod
	def database_connection():
		return mdb.connect(manager._MYSQL_HOST,
                                   manager._MYSQL_USERNAME,
                                   manager._MYSQL_PASSWORD,
                                   manager._MYSQL_DB)

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
					                        WHERE status <> "DELETING"
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
					cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
					                  FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
					                        FROM ap_slice 
					                        WHERE status <> "DELETING"
					                        GROUP BY physical_ap) AS 
					                  A LEFT JOIN ap ON A.physical_ap = ap.name
					                  WHERE name = %s """, (request['physical_ap']))
					result = cursor.fetchall()

					if len(result) == 0:
						return 'No such physical ap named \'' + str(request['physical_ap']) + '\' exists!'

					ap = result[0]

					if ap[used_slice] + _ADDITIONAL_SLICE[command] > 4 * ap[number_radio]: #We create new slice
						return 'The AP \'' + str(ap[name]) + '\' has no space left to execute command \'' + command + '\'.'
						#Else return None later

        	except mdb.Error, e:
            		print "Error %d: %s" % (e.args[0], e.args[1])
            		sys.exit(1)
           	except Exception, e:
           			print "Error %d: %s" % (e.args[0], e.args[1])
           			sys.exit(1)
		return None 
		
#See RadioConfigInvalid exception for what this class is verifying
class RadioConfigExistedVerification(RequestVerification):
	def _verify(self, command, request):
		check_result = self._check_radio_config_existed(command, request)
		if check_result:
			raise RadioConfigInvalid(check_result)

	def _check_radio_config_existed(self, command, request):
		if request is None:
			return None
		else:
			#Check for existed configuration on ap radio using the request
			try:
				con = RequestVerification.database_connection() 
				with con:
					cursor = con.cursor()

					name = 0
					used_slice = 1
					number_radio = 2

					cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
					                  FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
					                        FROM ap_slice 
					                        WHERE status <> "DELETED"
					                        GROUP BY physical_ap) AS 
					                  A LEFT JOIN ap ON A.physical_ap = ap.name
					                  WHERE name = %s""", (request['physical_ap']))

					result = cursor.fetchall()
					config_existed = len(result) != 0 #This does not take into consideration the fact that there
													  #can be more than 1 radios and the requested radio has not been
													  # configured yet.
					radio_interface = request['config']['RadioInterfaces']
					if len(radio_interface) == 0:
						request_has_config = True
					else:
						request_has_config = radio_interface[0]['flavor'] == "wifi_radio"

					if config_existed and request_has_config:
						return "Radio for the ap " + request['physical_ap'] + " has already been configured. Cannot change the radio's configurations."
					elif (not config_existed) and (not request_has_config):
						return "Radio for the ap " + request['physical_ap'] + " has not been configured. An initial configuration is required."
        	except mdb.Error, e:
            		print "Error %d: %s" % (e.args[0], e.args[1])
            		sys.exit(1)
           	except Exception, e:
           			print "Error %d: %s" % (e.args[0], e.args[1])
           			sys.exit(1)
		return None 

class VirtualInterfaceVerification(RequestVerification):
	def _verify(self, command, request):
		check_result = self._check_number_of_virtual_interface(command, request)
		if check_result:
			raise RadioConfigInvalid(check_result)

	def _check_number_of_virtual_interface(self, command, request):
		if request is None:
			return None
		else:
			#Check for number of VirtualInterface in the request
			number_of_virtual_interface = len(request['config']['VirtualInterfaces'])
			if number_of_virtual_interface != 2:
				return "Attempt to create slice with " + number_of_virtual_interface + ". Exactly two VirtualInterface is required."
		return None

#Base abstract class for all exception raised (when conflict detected)
class VerificationException(exception.AuroraException):
	__metaclass__ = ABCMeta
	
	@abstractmethod
	def _handle_exception(self):
	    #Tell the client of the problem here or resolve internally
		pass

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
				return ex._handle_exception()
		return None


#Use this method as an interface for the verification. Internal structure above must not be accessed from outside of the file
def verifyOK(request = None):
	if request is None:
		command = GENERAL_CHECK
	else:
		command = request['command']
	RequestVerifier.isVerifyOK(command, request)

if __name__ == '__main__':
    #Testing
    isVerifyOK(CREATE_SLICE, {})