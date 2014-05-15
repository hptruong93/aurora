# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

import sys


class BaseException(Exception):
    """An error occurred."""
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.message or self.__class__.__doc__


class CommandError(BaseException):
    """Invalid usage of CLI"""

class HTTPException(BaseException):
    """
The base exception class for all exceptions this library raises.
"""
    def __init__(self, code, message=None, details=None):
        self.code = code
        self.message = message or self.__class__.message
        self.details = details

    def __str__(self):
        return "%s (HTTP %s)" % (self.message, self.code)


class HTTPMultipleChoices(HTTPException):
    code = 300

    def __str__(self):
        self.details = ("Requested version of OpenStack Management API is not"
                        "available.")
        return "%s (HTTP %s) %s" % (self.__class__.__name__, self.code,
                                    self.details)


class HTTPBadRequest(HTTPException):
    code = 400


class HTTPUnauthorized(HTTPException):
    code = 401


class HTTPForbidden(HTTPException):
    code = 403

class HTTPNotFound(HTTPException):
    code = 404


class HTTPMethodNotAllowed(HTTPException):
    code = 405

class HTTPConflict(HTTPException):
    code = 409

class HTTPInternalServerError(HTTPException):
    code = 500


class HTTPNotImplemented(HTTPException):
    code = 501


class HTTPBadGateway(HTTPException):
    code = 502


class HTTPServiceUnavailable(HTTPException):
    code = 503


_code_map = dict((c.code, c) for c in [HTTPBadRequest,
                                              HTTPUnauthorized,
                                              HTTPForbidden,
                                              HTTPNotFound,
                                              HTTPMethodNotAllowed,
                                              HTTPNotImplemented,
                                              HTTPServiceUnavailable])

def from_response(response, body):
    
    cls = _code_map.get(response.status_code, HTTPException)
    if body:
        if hasattr(body, 'keys'):
            error = body[body.keys()[0]]
            message = error.get('message', None)
            details = error.get('details', None)
        else:
            message = "Unable to communicate with management service: %s." % body
            details = None
        return cls(code=response.status_code, message=message, details=details)
    else:
        return cls(code=response.status_code)

class SSLConfigurationError(BaseException):
    pass


class SSLCertificateError(BaseException):
    pass
