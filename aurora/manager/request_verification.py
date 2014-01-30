from abc import ABCMeta, abstractmethod

import sys
sys.path.insert(0,'../ap/')

import exception
import MySQLdb as mdb
import manager

GENERAL_CHECK = 'general_check'

#Base abstract class for all verification
class RequestVerification():
	__metaclass__ = ABCMeta
	
	#This method return a connection to mysql database
	#This method must be wrapped by a try catch block (catching mdb.Error)
	@staticmethod
	def _connect_database():
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
			'wslice_add' : 1
		}
		
		
		try:
			con = RequestVerification._connect_database() 
			with con:
				cursor = con.cursor()

				name = 0
				used_slice = 1
				number_radio = 2

				if not request:
					cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
					                  FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
					                        FROM ap_slice GROUP BY physical_ap) AS 
					                  A LEFT JOIN ap ON A.physical_ap = ap.name""")
					result = cursor.fetchall()
					
					for ap in result:
						if ap[used_slice] > 4 * ap[number_radio]:
							return 'The AP ' + str(ap[name]) + ' has no space left to create new slice.'
							#Else return None later
					#print result #For testing only
				else:
					cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
					                  FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
					                        FROM ap_slice GROUP BY physical_ap) AS 
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
		
#Base abstract class for all exception raised (when conflict detected)
class VerificationException(exception.AuroraException):
	__metaclass__ = ABCMeta
	
	@abstractmethod
	def _handle_exception(self):
		pass

#This exception is raised when an AP is having, or is requested to have more than 4n ap slices with n is the AP's number of radios
class NoAvailableSpaceLeftInAP(VerificationException):
	def __init__(self, message = ""):
		self.message = message
		super(NoAvailableSpaceLeftInAP, self).__init__(message)
	
	def _handle_exception(self):
	    #Tell the client of the problem here or resolve internally
		return self.message

class RequestVerifier():
	#The command names must be identical to the method calling
	#verification from aurora_db.py
	_commands = {
	    'general_check' : [APSliceNumberVerification()],
		'wslice_add' : [APSliceNumberVerification()]
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
def verifyOK(command = GENERAL_CHECK, request = None):
	RequestVerifier.isVerifyOK(command, request)

if __name__ == '__main__':
    #Testing
    isVerifyOK('wslice_add', {'physical_ap' : 'openflow'})