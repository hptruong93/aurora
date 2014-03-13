from abc import ABCMeta, abstractmethod
import sys

from aurora import exc as exception


#Base abstract class for all exception raised (when conflict detected)
class VerificationException(exception.AuroraException):
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def _handle_exception(self):
        #Tell the client about the problem here or resolve internally
        pass

#This exception is raised when the verifier cannot find a key in the request. It would provide the client the name of the missing key
class MissingKeyInRequest(VerificationException):
    def __init__(self, message = "not_provided"):
        self.message = message
        super(MissingKeyInRequest, self).__init__(message)
    
    def _handle_exception(self):
        return 'Key \'' + self.message + '\' could not be found. Please check request!'

#This exception is raised when the verifier cannot find the ap mentioned in the request, either in the database or the
#provision folder of manager
class NoSuchAPExists(VerificationException):
    def __init__(self, message = "not_provided"):
        self.message = message
        super(NoSuchAPExists, self).__init__(message)
    
    def _handle_exception(self):
        return "Cannot find any AP named \'" + self.message + "\'"

#This exception is raised when the verifier cannot find the slice mentioned in the request, either in the database or the
#provision folder of manager
class NoSuchSliceExists(VerificationException):
    def __init__(self, message = "not_provided"):
        self.message = message
        super(NoSuchSliceExists, self).__init__(message)
    
    def _handle_exception(self):
        return "Cannot find any slice named \'" + self.message + "\'"

#This exception is raised when an AP is having, or is requested to have more than 4n ap slices with n is the AP's number of radios
class NoAvailableSpaceLeftInAP(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(NoAvailableSpaceLeftInAP, self).__init__(message)
    
    def _handle_exception(self):
        return self.message

#This exception is raised when the client's operation would result in:
#	There would be two configurations for one radio
#	There would be no configuration for the radio which a slice will be created on/ has existing slices
class RadioConfigInvalid(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(RadioConfigInvalid, self).__init__(message)

    def _handle_exception(self):
        return self.message

#This exception is raised when the client attempts to create a new slice and provide an invalid number of Bridge
#The number of Bridge expected is one.
class BridgeNumberInvalid(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(BridgeNumberInvalid, self).__init__(message)

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

#This exception is raised when a client attempts to create a new slice with bridge/ virtual interface similar to another client
#Different client should have different bridge and virtual interfaces.
class AccessConflict(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(AccessConflict, self).__init__(message)

    def _handle_exception(self):
        return self.message

#This exception is raised when a client attempts to specify a bandwidth greater than the ap's capacity (this value is determined through practical observation. See other documents).
class InsufficientBandwidth(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(InsufficientBandwidth, self).__init__(message)

    def _handle_exception(self):
        return self.message

#This exception is raised when a client attempts to delete a slice while there are more than 1 slice in the ap, and that
#the deleting slice is the main slice that contains radio configuration.
class IllegalSliceDeletion(VerificationException):
    def __init__(self, message = ""):
        self.message = message
        super(IllegalSliceDeletion, self).__init__(message)

    def _handle_exception(self):
        return self.message