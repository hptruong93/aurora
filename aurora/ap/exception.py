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

class FlavourNotExist(AuroraException):
    message = "Flavour does not exist!"
    
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
    
class InstanceNotFound(AuroraException):
    message = "The instance does not exist."

