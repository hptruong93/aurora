# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#
"""Simple Manager HTTP Server for communicating JSON configuration 
files between Aurora Manager and Client.

A possible entry point for starting manager is :func:`main()`.

"""

import BaseHTTPServer
import json
import logging
import urlparse
from pprint import pprint
import os
import sys
import traceback
from SocketServer import ThreadingMixIn
import threading
import Queue
import time

from aurora import config
from aurora import stop_thread
from aurora import cls_logger
from aurora import manager
from aurora.exc import *

LOGGER = logging.getLogger(__name__)


CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
RESPONSES = {}
last_response = 0

class NewConnectionHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handles client HTTP requests.

    A new NewConnectionHandler is created for every incoming 
    connection received by :class:`ManagerServer`.  The handler 
    defines the behavior upon receipt of a GET or POST HTTP message.
    The communication structure is such that a client will first post 
    a message containing a configuration JSON which be passed to 
    :class:`aurora.manager.Manager`, and will then follow up with a 
    GET request for feedback about execution of the issued command.

    Only one instance of :class:`aurora.manager.Manager` will be 
    created, and a handle for this instance is stored in 
    ``NewConnectionHandler.MANAGER``.

    """
    server_version= "Aurora/0.2"
    MANAGER = None

    # Override __init__ to instantiate Manager, pass along parameters:
    # BaseHTTPServer.BaseHTTPRequestHandler(request, client_address, 
    #                                       server)
    def __init__(self, *args):
        """Verifies an :class:`aurora.manager.Manager` instance exists 
        to handle client requests.

        :param args args: Arguments to set up 
            :class:`BaseHTTPServer.BaseHTTPRequestHandler`

        """
        self.LOGGER = cls_logger.get_cls_logger(self)
        if NewConnectionHandler.MANAGER == None:
            self.LOGGER.info("Error: No manager to handle request.")
            sys.exit(1)

        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
    
    # __del__ does not override anything
    def __del__(self):
        #print "Destructing NewConnectionHandler"
        pass
        
    def do_GET(self):
        """Handles a GET request.

        Sends a 200-OK response with the data from the response file.

        """

        parsed_path = urlparse.urlparse(self.path)
        try:
            params = dict([p.split('=') for p in parsed_path[4].split('&')])
        except:
            params = {}
        LOGGER.info('Client retrieving request with id: ' + str(params['request_id']))

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        
        #Open response file
        try:
            response = RESPONSES[params['request_id']]
        except:
            response = {"status": False ,"message":"Response not found for the request"}
        self.wfile.write(response)
        RESPONSES.pop(params['request_id'], None)

    def do_POST(self):
        """Handles a POST request.

        Parses some aspects of the request to determine what function 
        is being requested, as well as which tenant, project, and user 
        the request belongs to.  Passes the command to 
        :func:`aurora.manager.Manager.parseargs`, and stores the 
        returned response.  This response will later be relayed back to 
        the client by a client GET request.

        """

        global last_response
        #If the manager HTTP server was idle in the last 30s, then all responses must have expired
        #If so, clear all responses
        if time.time() - last_response > 20: 
            RESPONSES.clear()
            LOGGER.info("HTTP server has been idle for the last 20s. Responses cleared") 
        last_response = time.time()

        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        JSONfile = json.loads(data_string)
        self.LOGGER.debug(JSONfile['function'])

        request_id = JSONfile['request_id']

        function = JSONfile['function']
        parameters = JSONfile['parameters']

        # The following are used to determine who is creating a slice.
        # Defaults are all -1
        tenant_id = JSONfile.get('tenant_id') or -1
        project_id = JSONfile.get('project_id') or -1
        user_id = JSONfile.get('user_id') or -1
        
        # Put in queue to wait to send to manager.py
        # Format of response:
        # {"status":(true of false) ,"message":"string if necessary"}
        response = NewConnectionHandler.MANAGER.parseargs(
                    function, parameters, tenant_id,
                    user_id, project_id
        )
        RESPONSES[request_id] = response

        # Begin the response
        self.send_response(200)
        self.end_headers()
        
    
    # Sends a document, unused
    def sendPage( self, type, body ):
        """Sends a page to a client.  Unused at the moment.

        :param str type: Type of data being sent ex. ``'application/json'``
        :param body: Data to send to client.

        """
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
        

class ManagerServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    """Builds upon :class:`BaseHTTPServer.HTTPServer`.

    Includes a logger, instantiates a :class:`aurora.manager.Manager` 
    instance and stores a static reference for it in 
    ``self.RequestHandlerClass``.  Also handles cleanup on exit.

    """
    def serve_forever(self):
        """Run to start the ManagerServer."""
        self.LOGGER = cls_logger.get_cls_logger(self)

        # Manager is now in server instance's scope, will be 
        # deconstructed upon interrupt. 
        self.manager = manager.Manager()

        # When initialized, handler_class from main is stored in 
        # RequestHandlerClass
        self.RequestHandlerClass.MANAGER = self.manager

        BaseHTTPServer.HTTPServer.serve_forever(self)
    
    def server_close(self):
        """Run to close the ManagerServer."""
        self.LOGGER.info("Closing HTTP server...")
        # Delete all references to manager so it destructs
        self.manager.stop()

        BaseHTTPServer.HTTPServer.server_close(self)
        self.LOGGER.info("HTTP server closed!")

def main():
    """An entry point for launching Aurora Manager.

    Sets up root-level logger.  Assigns a the request handler class.
    Starts the HTTP server :class:`ManagerServer`.  Performs some basic
    error handling and outputs tracebacks.

    The logging level can be specified from command line arguments.

    .. seealso:: :mod:`aurora.shell`

    """
    level = logging.INFO
    if len(sys.argv) > 1:
        level = sys.argv[1]
        if level == "DEBUG":
            level = logging.DEBUG
        elif level == "INFO":
            level = logging.INFO
        elif level == "WARN" or level == "WARNING":
            level = logging.WARN
        elif level == "ERROR":
            level = logging.ERROR
        elif level == "CRITICAL":
            level = logging.CRITICAL
        else:
            level = logging.INFO

    # print level
    cls_logger.set_up_root_logger(level=level)
    
    handler_class=NewConnectionHandler
    server_address = (config.CONFIG['manager']['host'], int(config.CONFIG['manager']['port']))
    try:
        msrvr = ManagerServer(server_address, handler_class)
        LOGGER.info("Starting webserver...")
        msrvr.serve_forever()
        
    except KeyboardInterrupt, KeyboardInterruptStopEvent:
        LOGGER.info("Shutting down webserver...")
        msrvr.server_close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

if __name__ == "__main__":
    LOGGER = logging.getLogger('manager_http_server')
    main()
