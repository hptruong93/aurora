from abc import ABCMeta, abstractmethod

import sys
sys.path.insert(0,'../ap/')

import exception
import MySQLdb as mdb
import manager

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
	def _verify(self, request):
		pass


class APSliceNumberVerification(RequestVerification):
	def _verify(self, request = None):
		check_result = self._check_number_of_ap_slice(request)
		if check_result:
			raise NoAvailableSpaceLeftInAP(check_result)

    #If request = None, it checks for inconsistency in the database, namely an AP with n radios should not have more than 4n ap slices
    #If request != None, it checks for the ap requested for available space.
    #The method raises a NoAvailableSpaceLeftInAP exception if there is any conflict.
	def _check_number_of_ap_slice(self, request):
		try:
     			con = RequestVerification._connect_database() 
			with con:
				cursor = con.cursor()
				if request is None:
					cursor.execute("""SELECT name, used_slice, number_radio, number_radio_free 
					                  FROM (SELECT physical_ap, COUNT(physical_ap) AS used_slice 
					                        FROM ap_slice GROUP BY physical_ap) AS 
					                  A LEFT JOIN ap ON A.physical_ap = ap.name""")
					result = cursor.fetchall()
					name = 0
					used_slice = 1
					number_radio = 2
					for ap in result:
						if ap[used_slice] < 4 * ap[number_radio]:
							return ap[name]
					#print result #For testing only
			
        	except mdb.Error, e:
            		print "Error %d: %s" % (e.args[0], e.args[1])
            		sys.exit(1)
		return None 

	def _get_physical_ap(self, request):
	    if not request:
	        raise Exception("Argument request cannot be None")
		return None
		
#Base abstract class for all exception raised (when conflict detected)
class VerificationException(exception.AuroraException):
	__metaclass__ = ABCMeta
	
	@abstractmethod
	def _handle_exception(self):
		pass

#This exception is raised when an AP is having, or is requested to have more than 4n ap slices with n is the AP's number of radios
class NoAvailableSpaceLeftInAP(VerificationException):
	def __init__(self, ap_name = ""):
		super(NoAvailableSpaceLeftInAP, self).__init__("The AP " + ap_name + " has no space left to create new slice.")
	
	def _handle_exception(self):
	    #Tell the client of the problem here or resolve internally
		pass


#Use this class as an interface for verification. Internal structure above should not be accessed from outside of this file.
class RequestVerifier():
	_verifier = [APSliceNumberVerification()]

	@staticmethod
	def verify(request = None):
		for verifier in RequestVerifier._verifier:
			try:
				verifier._verify(request)
			except VerificationException as ex:
				ex._handle_exception()
		return None

#Testing
RequestVerifier.verify()
