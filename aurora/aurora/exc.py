# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#
"""Module containing exceptions for use in Aurora Manager."""

#---------
# Base Exception for Aurora program
#
class AuroraException(Exception):
    """Base class for exceptions in Aurora.
    Inherit it and define info to use it.

    An inherited class should include an overridden ``message``, which
    can contain key word arguments such as ``%(kw)s``.  These will be 
    substituted upon raising your exception::

        raise MyAuroraException(kw="my keyword string")

    """
    
    # Based on OpenStack Nova exception setup
    # https://github.com/openstack/nova/blob/master/nova/exception.py
    message = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if not message:
            try:
                self.message = self.message % kwargs

            except Exception:
                self.message = AuroraException.message
                # message = self.message

        super(AuroraException, self).__init__(self.message)

#---------
# Config DB related exceptions
#
class NoSliceIDInConfiguration(AuroraException):
    message = "No slice ID available in configuration."

class ModifyConfigNotImplemented(AuroraException):
    message = "Modify config in DB isn't implemented."

class NoConfigExistsError(AuroraException):
    message = "No file for slice:%(slice)s exists in the DB."

class CannotCreateTenantConfigDir(AuroraException):
    message = "Cannot create the config DB directory %(dir_path)s"

#---------
# Aurora DB Status-related exceptions
#
class InvalidStatusUpdate(AuroraException):
    message = "Cannot update status %(status)s"

class InvalidPENDINGStatusUpdate(InvalidStatusUpdate):
    message = "Cannot change status %(status)s to 'PENDING'"

class InvalidACTIVEStatusUpdate(InvalidStatusUpdate):
    message = "Cannot change status %(status)s to 'ACTIVE'"

class DOWNtoPENDINGStatusUpdateWarning(InvalidStatusUpdate):
    message = "Slice %(ap_slice_id)s is 'DOWN', not updating to 'PENDING'"

#---------
# Aurora DB related exceptions
#
class NoAPNameGivenException(AuroraException):
    message = "Cannot set AP status for unspecified AP"

class InvalidAPNameTypeException(AuroraException):
    message = "Please enter a valid ap_name"

class NoWnetExistsForTenantException(AuroraException):
    message = "No wnets exist"

class NoWnetNameExistsForTenantException(AuroraException):
    message = "Wnet %(wnet)s does not exist"

class APSliceAlreadyInWnetException(AuroraException):
    message = "AP Slice %(ap_slice_id)s already in '%(wnet)s'"

class NoSliceExistsException(AuroraException):
    message = "No slice %(ap_slice_id)s exists"

#---------
# Provision Server exceptions
#
class RequestInvalidConfigFileNameException(AuroraException):
    message = "File names outside directory not permitted"

#---------
# Slice plugin exceptions
#
class InvalidCapsulatorConfigurationException(AuroraException):
    message = "The capsulator configuration given is invalid"

#---------
# Manager related exceptions
#
class NoSliceConfigFileException(AuroraException):
    message = "No slice configuration file found"

class KeyboardInterruptStopEvent(Exception):
    message = "Stopping webserver"

#---------
# Dispatcher related exceptions
#
class MessageSendAttemptWhileClosing(AuroraException):
    message = "Tried to dispatch while dispatcher is closing"

class DispatchTimeout(AuroraException):
    message = "A timeout occured during dispatch"

class DispatchLockedForAPTimeout(DispatchTimeout):
    message = "Timeout occured during dispatch for %(ap)s"

class DispatchWaitForOpenChannelTimeout(DispatchTimeout):
    message = "Timeout occured waiting for open channel during dispatch"