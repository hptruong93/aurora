# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2013, The SAVI Project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import json

import eventlet.wsgi
import routes.middleware
import ssl
import webob.dec
import webob.exc

from janus.common import logging
from janus import exception
from janus.openstack.common import jsonutils
from janus import config

CONF = config.CONF

LOG = logging.getLogger(__name__)

# Environment variable used to pass the request context
CONTEXT_ENV = 'savi.context'


# Environment variable used to pass the request params
PARAMS_ENV = 'savi.params'


class SmarterEncoder(json.JSONEncoder):
    """Help for JSON encoding dict-like objects."""
    def default(self, obj):
        if not isinstance(obj, dict) and hasattr(obj, 'iteritems'):
            return dict(obj.iteritems())
        return super(SmarterEncoder, self).default(obj)


class WritableLogger(object):
    """A thin wrapper that responds to `write` and logs."""

    def __init__(self, logger, level=logging.DEBUG):
        self.logger = logger
        self.level = level

    def write(self, msg):
        self.logger.log(self.level, msg)


class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, application, host=None, port=None, threads=1000):
        self.application = application
        self.host = host or '0.0.0.0'
        self.port = port or 0
        self.pool = eventlet.GreenPool(threads)
        self.socket_info = {}
        self.greenthread = None
        self.do_ssl = False
        self.cert_required = False

    def start(self, key=None, backlog=128):
        """Run a WSGI server with the given application."""
        LOG.debug(_('Starting %(arg0)s on %(host)s:%(port)s') %
                  {'arg0': sys.argv[0],
                   'host': self.host,
                   'port': self.port})
        socket = eventlet.listen((self.host, self.port), backlog=backlog)
        if key:
            self.socket_info[key] = socket.getsockname()
        # SSL is enabled
        if self.do_ssl:
            if self.cert_required:
                cert_reqs = ssl.CERT_REQUIRED
            else:
                cert_reqs = ssl.CERT_NONE
            sslsocket = eventlet.wrap_ssl(socket, certfile=self.certfile,
                                          keyfile=self.keyfile,
                                          server_side=True,
                                          cert_reqs=cert_reqs,
                                          ca_certs=self.ca_certs)
            socket = sslsocket

        self.greenthread = self.pool.spawn(self._run, self.application, socket)

    def set_ssl(self, certfile, keyfile=None, ca_certs=None,
                cert_required=True):
        self.certfile = certfile
        self.keyfile = keyfile
        self.ca_certs = ca_certs
        self.cert_required = cert_required
        self.do_ssl = True

    def kill(self):
        if self.greenthread:
            self.greenthread.kill()

    def wait(self):
        """Wait until all servers have completed running."""
        try:
            self.pool.waitall()
        except KeyboardInterrupt:
            pass

    def _run(self, application, socket):
        """Start a WSGI server in a new green thread."""
        log = logging.getLogger('eventlet.wsgi.server')
        eventlet.wsgi.server(socket, application, custom_pool=self.pool,
                             log=WritableLogger(log))


class Request(webob.Request):
    pass


class Application(object):
    @classmethod
    def factory(cls, global_config, **local_config):
        return cls()
    @webob.dec.wsgify
    def __call__(self, req):
        arg_dict = req.environ['wsgiorg.routing_args'][1]
        action = arg_dict.pop('action')
        del arg_dict['controller']
        #LOG.debug(_('arg_dict: %s'), arg_dict)

        # allow middleware up the stack to provide context & params
        context = req.environ.get(CONTEXT_ENV, {})
        context['query_string'] = dict(req.params.iteritems())
        params = req.environ.get(PARAMS_ENV, {})
        
        params.update(arg_dict)

        method = getattr(self, action)

        # NOTE(vish): make sure we have no unicode keys for py2.6.
        params = self._normalize_dict(params)

        try:
            result = method(req, **params)
        except exception.Error as e:
            LOG.warning(e)
            return render_exception(e)
        except Exception as e:
            logging.exception(e)
            return render_exception(exception.UnexpectedError(exception=e))

        if result is None:
            return render_response(status=(204, 'No Content'))
        elif isinstance(result, basestring):
            return result
        elif isinstance(result, webob.Response):
            return result
        elif isinstance(result, webob.exc.WSGIHTTPException):
            return result
        return render_response(body=result)

    def _normalize_arg(self, arg):
        return str(arg).replace(':', '_').replace('-', '_')

    def _normalize_dict(self, d):
        return dict([(self._normalize_arg(k), v)
                     for (k, v) in d.iteritems()])



class Middleware(Application):
    """Base WSGI middleware.

These classes require an application to be
initialized that will be called next. By default the middleware will
simply call its wrapped app, or you can override __call__ to customize its
behavior.

"""

    @classmethod
    def factory(cls, global_config, **local_config):
        """Used for paste app factories in paste.deploy config files.

Any local configuration (that is, values under the [filter:APPNAME]
section of the paste config) will be passed into the `__init__` method
as kwargs.

A hypothetical configuration would look like:

[filter:analytics]
redis_host = 127.0.0.1
paste.filter_factory = nova.api.analytics:Analytics.factory

which would result in a call to the `Analytics` class as

import nova.api.analytics
analytics.Analytics(app_from_paste, redis_host='127.0.0.1')

You could of course re-implement the `factory` method in subclasses,
but using the kwarg passing it shouldn't be necessary.

"""
        def _factory(app):
            conf = global_config.copy()
            conf.update(local_config)
            return cls(app)
        return _factory

    def __init__(self, application):
        self.application = application

    def process_request(self, request):
        """Called on each request.

If this returns None, the next application down the stack will be
executed. If it returns a response then that response will be returned
and execution will stop here.

"""
        return None

    def process_response(self, request, response):
        """Do whatever you'd like to the response, based on the request."""
        return response

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        response = self.process_request(request)
        if response:
            return response
        response = request.get_response(self.application)
        return self.process_response(request, response)


class Debug(Middleware):
    """Helper class for debugging a WSGI application.

Can be inserted into any WSGI application chain to get information
about the request and response.

"""

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, req):
        LOG.debug('%s %s %s', ('*' * 20), 'REQUEST ENVIRON', ('*' * 20))
        for key, value in req.environ.items():
            LOG.debug('%s = %s', key, value)
        LOG.debug('')
        LOG.debug('%s %s %s', ('*' * 20), 'REQUEST BODY', ('*' * 20))
        for line in req.body_file:
            LOG.debug(line)
        LOG.debug('')

        resp = req.get_response(self.application)

        LOG.debug('%s %s %s', ('*' * 20), 'RESPONSE HEADERS', ('*' * 20))
        for (key, value) in resp.headers.iteritems():
            LOG.debug('%s = %s', key, value)
        LOG.debug('')

        resp.app_iter = self.print_generator(resp.app_iter)

        return resp

    @staticmethod
    def print_generator(app_iter):
        """Iterator that prints the contents of a wrapper string."""
        LOG.debug('%s %s %s', ('*' * 20), 'RESPONSE BODY', ('*' * 20))
        for part in app_iter:
            LOG.debug(part)
            yield part


class Router(object):
    """WSGI middleware that maps incoming requests to WSGI apps."""

    def __init__(self, mapper):
        """Create a router for the given routes.Mapper."""
        self.map = mapper
        log = logging.getLogger('routes.middleware')
        log.setLevel(CONF.logging.routes)
        self._router = routes.middleware.RoutesMiddleware(self._dispatch,
                                                          self.map)
    @classmethod
    def factory(cls, global_conf, **local_conf):
        return cls(routes.Mapper())

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, req):
        """Route the incoming request to a controller based on self.map.

If no match, return a 404.

"""
        return self._router

    @staticmethod
    @webob.dec.wsgify(RequestClass=Request)
    def _dispatch(req):
        """Dispatch the request to the appropriate controller.

Called by self._router after matching the incoming request to a route
and putting the information into req.environ. Either returns 404
or the routed WSGI app's response.

"""
        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            return render_exception(
                exception.NotFound(_('The resource could not be found.')))
        app = match['controller']
        return app


def render_response(body=None, status=None, headers=None):
    """Forms a WSGI response."""
    headers = headers or []
    headers.append(('Vary', 'X-Auth-Token'))

    if body is None:
        body = ''
        status = status or (204, 'No Content')
    else:
        body = jsonutils.dumps(body, cls= SmarterEncoder)
        headers.append(('Content-Type', 'application/json'))
        status = status or (200, 'OK')

    return webob.Response(body=body,
                          status='%s %s' % status,
                          headerlist=headers)


def render_exception(error):
    """Forms a WSGI response based on the current error."""
    return render_response(status=(error.code, error.title), body={
        'error': {
            'code': error.code,
            'title': error.title,
            'message': str(error),
        }
    })
