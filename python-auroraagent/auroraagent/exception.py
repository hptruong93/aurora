# Handles custom exceptions for the Aurora program
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

class AuroraException(Exception):
    """Base class for exceptions in Aurora.
    Inherit it and define info to use it."""
    
    # Based on OpenStack Nova exception setup
    # https://github.com/openstack/nova/blob/master/nova/exception.py
    message = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if not message:
            try:
                message = self.message % kwargs

            except Exception:
                message = self.message

        super(AuroraException, self).__init__(message)

class FlavorNotExist(AuroraException):
    message = "Flavor does not exist!"
    
class ModuleNotLoaded(AuroraException):
    message = "Module not found in loaded module list."
    
class PIDNotFound(AuroraException):
    message = "PID Not found."
    
class CommandNotFound(AuroraException):
    message = "Command is either not valid or not allowed."
    
class BridgeNotFound(AuroraException):
    message = "The bridge does not exist."
    
class SliceNotFound(AuroraException):
    message = "The slice does not exist."

class SliceRadioNotFound(AuroraException):
    message = "The slice radio can not be found."

class InstanceNotFound(AuroraException):
    message = "The instance does not exist."
    
class NameAlreadyInUse(AuroraException):
    message = "The name is already in the database."
    
class EntryNotFound(AuroraException):
    message = "The entry does not exist in the database."
    
class InvalidConfig(AuroraException):
    message = "The configuration file is not valid."
    
class SliceCreationFailed(AuroraException):
    message = "Unable to create slice."

class SliceRecreationFailed(AuroraException):
    message = "Unable to recreate slice."

class SliceModificationFailed(AuroraException):
    message = "Unable to modify slice."
    
class ReachedBSSLimitOnRadio(AuroraException):
    message = "No more BSS are permitted on this radio."
    
class InvalidKey(AuroraException):
    message = "Key specified is not valid for the encryption type."
    
class InvalidSSID(AuroraException):
    message = "SSID not valid; must not be None or an empty string."
    
class InvalidEncryption(AuroraException):
    message = "Encryption type not valid."
    
class hostapdError(AuroraException):
    message = "An error occured with hostapd.  Check settings."
    
class disabledError(AuroraException):
    message = "The radio must be active to execute this function."

class NoUserIDForSlice(AuroraException):
    message = "No user id was found for the slice in question."