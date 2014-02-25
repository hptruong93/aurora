# Simple Manager HTTP Server for receiving JSON files (Adapted from Micheal Smith's Code)

import BaseHTTPServer
import json
import logging
from pprint import pprint
import sys

import cls_logger
import manager

LOGGER = logging.getLogger(__name__)


class NewConnectionHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version= "Aurora/0.2"
    MANAGER = None

    # Override __init__ to instantiate Manager, pass along parameters:
    # BaseHTTPServer.BaseHTTPRequestHandler(request, client_address, server)
    def __init__(self, *args):
        self.LOGGER = cls_logger.get_cls_logger(self)
        if NewConnectionHandler.MANAGER == None:
            self.LOGGER.info("Error: No manager to handle request.")
            sys.exit(1)
        #print "\nConstructing NewConnectionHandler using", NewConnectionHandler.MANAGER
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
    
    # __del__ does not override anything
    def __del__(self):
        #print "Destructing NewConnectionHandler"
        pass
        
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        
        #Open response file
        RESPONSEFILE = open('core/json/response.json', 'r')
        response = json.load(RESPONSEFILE)
        
        self.wfile.write(response)
    
    def do_POST(self):
        # Clear previous response file (if exists)
        default_response = {}
        default_response['status'] = False
        default_response['message'] = ""
        RESPONSE_FILE = open('core/json/response.json', 'w')
        json.dump(default_response, RESPONSE_FILE, sort_keys=True, indent=4)
        RESPONSE_FILE.close()
        
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        JSONfile = json.loads(data_string)
        self.LOGGER.debug(JSONfile['function'])

        # Begin the response
        self.send_response(200)
        self.end_headers()
        
        #Send to manager.py
        #Format of response: {"status":(true of false) ,"message":"string if necessary"}
        response = NewConnectionHandler.MANAGER.parseargs(JSONfile['function'], JSONfile['parameters'], 1,1,1)
        self.LOGGER.debug(response['message'])

        #Save response to file
        RESPONSEFILE = open('core/json/response.json', 'w')
        json.dump(response, RESPONSEFILE, sort_keys=True, indent=4)
        RESPONSEFILE.close()
    
    # Sends a document, unused
    def sendPage( self, type, body ):
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
        
class ManagerServer(BaseHTTPServer.HTTPServer):
    """Builds upon HTTPServer and also sets up and tears down single Manager() instance"""
    def serve_forever(self):
        self.LOGGER = cls_logger.get_cls_logger(self)

        # Manager is now in server instance's scope, will be deconstructed
        # upon interrupt
        self.manager = manager.Manager()
        # When initialized, handler_class from main is stored in RequestHandlerClass
        self.RequestHandlerClass.MANAGER = self.manager
        #self.LOGGER.debug(self.RequestHandlerClass.MANAGER)
        BaseHTTPServer.HTTPServer.serve_forever(self)
    
    def server_close(self):
        # Delete all references to manager so it destructs
        self.manager.stop()
        del self.manager, self.RequestHandlerClass.MANAGER
        
        BaseHTTPServer.HTTPServer.server_close(self) 

def main():
    cls_logger.set_up_root_logger()
    
    handler_class=NewConnectionHandler
    server_address = ('', 5554)
    try:
        msrvr = ManagerServer(server_address, handler_class)
        LOGGER.info("Starting webserver...")
        msrvr.serve_forever()

    except KeyboardInterrupt:
        if e:
            print e
        LOGGER.info("Shutting down webserver...")
        msrvr.server_close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

if __name__ == "__main__":
    LOGGER = logging.getLogger('manager_http_server')
    main()