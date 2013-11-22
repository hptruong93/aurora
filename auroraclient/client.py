'''
Created on Jan 7, 2013

@author: Mohammad Faraji<ms.faraji@utoronto.ca>
Edited by Kevin Han for Aurora
'''

import copy
import logging
import urlparse

import requests

from exc import *

try:
    import json
except ImportError:
    import simplejson as json

# Python 2.5 compat fix
if not hasattr(urlparse, 'parse_qsl'):
    import cgi
    urlparse.parse_qsl = cgi.parse_qsl


_logger = logging.getLogger(__name__)

class Client(object):

    USER_AGENT = 'python-auroraclient'

    def __init__(self, endpoint, token=None, cacert=None, key_file=None,
                 ssl_compression=None, cert_file=None, insecure=False, admin=False):
        """Construct a new http client
"""
        self.version = 'v1.0'
        self.admin = admin
        self.endpoint=endpoint
        if token:
            self.token = token
        else:
            self.token = None
        if cacert:
            self.verify_cert = cacert
        else:
            self.verify_cert = True
        if insecure:
            self.verify_cert = False
        self.cert = cert_file
        if cert_file and key_file:
            self.cert = (cert_file, key_file,)
            
    def serialize(self, entity):
        return json.dumps(entity)

    def request(self, url, method, **kwargs):
        request_kwargs = copy.copy(kwargs)
        request_kwargs.setdefault('headers', kwargs.get('headers', {}))
        request_kwargs['headers']['User-Agent'] = self.USER_AGENT
        if self.token:
            request_kwargs['headers']['X-Auth-Token'] = self.token
        if 'body' in kwargs:
            request_kwargs['headers']['Content-Type'] = 'application/json'
            request_kwargs['data'] = self.serialize(kwargs['body'])
            del request_kwargs['body']
        if self.cert:
            request_kwargs['cert'] = self.cert
        url_to_use = "%s/%s%s" % (self.endpoint,self.version,url)
        resp = requests.request(
            method,
            url_to_use,
            verify=self.verify_cert,
            **request_kwargs)
        if resp.status_code >= 400:
            _logger.debug(
                "Request returned failure status: %s",
                resp.status_code)
            raise exc.from_response(resp, resp.text)
        elif resp.status_code in (301, 302, 305):
            # Redirected. Reissue the request to the new location.
            return self.request(resp.headers['location'], method, **kwargs)

        if resp.text:
            try:
                body = json.loads(resp.text)
            except ValueError:
                body = None
                _logger.debug("Could not decode JSON from body: %s"
                              % resp.text)
        else:
            _logger.debug("No body was returned.")
            body = None
        return resp, body

    def get(self, url, **kwargs):
        return self.request(url, 'GET', **kwargs)

    def head(self, url, **kwargs):
        return self.request(url, 'HEAD', **kwargs)

    def post(self, url, **kwargs):
        return self.request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        return self.request(url, 'PUT', **kwargs)

    def patch(self, url, **kwargs):
        return self.request(url, 'PATCH', **kwargs)

    def delete(self, url, **kwargs):
        return self.request(url, 'DELETE', **kwargs)
