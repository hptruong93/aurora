# Base Exception for Aurora program

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

class NoSliceIDInConfiguration(AuroraException):
    message = "No slice ID available in configuration."

class ModifyConfigNotImplemented(AuroraException):
    message = "Modify config in DB isn't implemented."

class NoConfigExistsError(AuroraException):
    message = "No file for slice:%(slice)s exists in the DB."