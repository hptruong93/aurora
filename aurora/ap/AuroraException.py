# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

class AuroraException(Exception):
    """Base class for exceptions in Aurora.
    Inherit it and define info to use it."""
    
    # Based on OpenStack Nova exception setup
    # https://github.com/openstack/nova/blob/master/nova/exception.py
    message = _("An unknown exception occurred.")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if not message:
            try:
                message = self.message % kwargs

            except Exception:
                message = self.message

        super(NovaException, self).__init__(message)

class FlavourNotExist(AuroraException):
    message = "Flavour does not exist!"

