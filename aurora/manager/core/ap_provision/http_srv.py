import BaseHTTPServer
import json
import logging
import os
from pprint import pformat
import threading

from ..cls_logger import get_cls_logger
#from .. import cls_logger

LOGGER = logging.getLogger(__name__)


class ProvisionHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    
    def __init__(self, *args):
        self.LOGGER = get_cls_logger(self)
        self.LOGGER.info("Constructing...")
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET( self ):
        # Verify request type
        if self.path.startswith("/initial_ap_config_request/"):
            # Open file with name of everything after the request
            try:
                file_name = self.path[27:]
                if ".." in file_name:
                    raise Exception("File names outside directory not permitted.")
                config_file = json.dumps(json.load(open('core/ap_provision/' + file_name + '.json','r')))
                
            except:
                # File does not exist/ not permitted/ not json
                self.send_response(404)
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
server = BaseHTTPServer.HTTPServer(server_address, handler_class)

def run():
    global provision_running
    if not provision_running:

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        LOGGER.info("Starting provision server %s", server_thread)
        provision_running = True
    else:
        LOGGER.warning("Provision server already running")

def stop():
    LOGGER.info("Shutting down provision server...")
    server.shutdown()

