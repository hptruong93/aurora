#---------
# Base Exception for Aurora program
#
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

#---------
# Aurora DB related exceptions
#
class NoAPNameGivenException(AuroraException):
    message = "Cannot set AP status for unspecified AP"

class InvalidAPNameTypeException(AuroraException):
    message = "Please enter a valid ap_name"

class NoWnetExistsForTenantException(AuroraException):
    message = "Wnet %(wnet)s does not exist"

class APSliceAlreadyInWnetException(AuroraException):
    message = "AP Slice %(ap_slice_id)s already in '%(wnet)s'"