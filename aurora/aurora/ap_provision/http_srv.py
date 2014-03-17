import BaseHTTPServer
import json
import logging
import os
from pprint import pformat
import sys
import threading
import traceback

from aurora.cls_logger import get_cls_logger
from aurora.exc import *

LOGGER = logging.getLogger(__name__)


class ProvisionHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    _PROVISION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json/')

    def __init__(self, *args):
        self.LOGGER = get_cls_logger(self)
        self.LOGGER.info("Constructing...")
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET( self ):
        # Verify request type
        if self.path.startswith("/initial_ap_config_request/"):
            # Open file with name of everything after the request
            try:
                file_name = self.path[27:] + '.json'
                if ".." in file_name:
                    raise RequestInvalidConfigFileNameException()
                with open(os.path.join(self._PROVISION_DIR, file_name),'r') as CF:
                    config_file = json.dumps(json.load(CF))
                
            except RequestInvalidConfigFileNameException:
                # File does not exist/ not permitted/ not json
                self.send_response(404)
            except Exception:
                traceback.print_exc(file=sys.stdout)
            else:
                # File OK
                self.send_page("application/json", config_file)
        # Bad request
        else:
            self.send_response( 400 )
    
    # Not implemented
    def do_POST( self ):
        self.send_response( 400 )
    
    # Sends a document
    def send_page( self, type, body ):
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
    
# Globals definition for starting Provision Server

provision_running = False    
handler_class = ProvisionHandler
server_address = ('', 5555)
server = None

def run():
    global provision_running, server
    if not provision_running:
        server = BaseHTTPServer.HTTPServer(server_address, handler_class)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        LOGGER.info("Starting provision server %s", server_thread)
        provision_running = True
    else:
        LOGGER.warning("Provision server already running")

def stop():
    LOGGER.info("Shutting down provision server...")
    if provision_running:
        server.shutdown()

