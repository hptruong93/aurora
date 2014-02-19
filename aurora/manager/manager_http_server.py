# Simple Manager HTTP Server for receiving JSON files (Adapted from Micheal Smith's Code)

import BaseHTTPServer
import json
import logging
from pprint import pprint

import manager

LOGGER = logging.getLogger(__name__)


class NewConnectionHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version= "Aurora/0.2"
    MANAGER = None
    
    # Override __init__ to instantiate Manager, pass along parameters:
    # BaseHTTPServer.BaseHTTPRequestHandler(request, client_address, server)
    def __init__(self, *args):
        if NewConnectionHandler.MANAGER == None:
            print "Error: No manager to handle request."
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
        RESPONSEFILE = open('json/response.json', 'r')
        response = json.load(RESPONSEFILE)
        
        self.wfile.write(response)
    
    def do_POST(self):
        # Clear previous response file (if exists)
        default_response = {}
        default_response['status'] = False
        default_response['message'] = ""
        RESPONSEFILE = open('json/response.json', 'w')
        json.dump(default_response, RESPONSEFILE, sort_keys=True, indent=4)
        RESPONSEFILE.close()
        
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        JSONfile = json.loads(data_string)
        print " [x]",JSONfile['function']

        # Begin the response
        self.send_response(200)
        self.end_headers()
        
        #Send to manager.py
        #Format of response: {"status":(true of false) ,"message":"string if necessary"}
        response = NewConnectionHandler.MANAGER.parseargs(JSONfile['function'], JSONfile['parameters'], 1,1,1)
        print " [v]",response['message']

        #Save response to file
        RESPONSEFILE = open('json/response.json', 'w')
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
        # Manager is now in server instance's scope, will be deconstructed
        # upon interrupt
        self.manager = manager.Manager()
        # When initialized, handler_class from main is stored in RequestHandlerClass
        self.RequestHandlerClass.MANAGER = self.manager
        #print self.RequestHandlerClass.MANAGER
        BaseHTTPServer.HTTPServer.serve_forever(self)
    
    def server_close(self):
        # Delete all references to manager so it destructs
        self.manager.stop()
        del self.manager, self.RequestHandlerClass.MANAGER
        
        BaseHTTPServer.HTTPServer.server_close(self) 

def main():
    
    logging.basicConfig(level=logging.INFO, format="[%(name)s]: %(message)s")

    handler_class=NewConnectionHandler
    server_address = ('', 5554)
    try:
        msrvr = ManagerServer(server_address, handler_class)
        LOGGER.info("Starting webserver...")
        msrvr.serve_forever()

    except BaseException as e:
        if e:
            print e
        LOGGER.info("Shutting down webserver...")
        msrvr.server_close()

if __name__ == "__main__":
    LOGGER = logging.getLogger('manager_http_server')
    main()