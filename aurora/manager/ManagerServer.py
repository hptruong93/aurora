# Simple Manager HTTP Server for receiving JSON files (Adapted from Micheal Smith's Code)

import BaseHTTPServer
import json
from manager import *

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    manager = None
    
    # Override __init__ to instantiate Manager, pass along parameters:
    # BaseHTTPServer.BaseHTTPRequestHandler(request, client_address, server)
    def __init__(self, *args):
        if MyHandler.manager == None:
            print "Error: No manager to handle request."
            sys.exit(1)
        #print "\nConstructing MyHandler using", MyHandler.manager
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
    
    # __del__ does not override anything
    def __del__(self):
        #print "Destructing MyHandler"
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
        
        # Begin the response
        self.send_response(200)
        self.end_headers()
        
        #Send to manager.py
        #Format of response: {"status":(true of false) ,"message":"string if necessary"}
        response = MyHandler.manager.parseargs(JSONfile['function'], JSONfile['parameters'], 1,1,1)
        
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
        self.manager = Manager()

        # When initialized, handler_class from main is stored in RequestHandlerClass
        self.RequestHandlerClass.manager = self.manager
        #print self.RequestHandlerClass.manager
        BaseHTTPServer.HTTPServer.serve_forever(self)
    
    def server_close(self):
        # Delete all references to manager so it destructs
        del self.manager, self.RequestHandlerClass.manager

        BaseHTTPServer.HTTPServer.server_close(self) 

if __name__ == "__main__":
    handler_class=MyHandler
    server_address = ('', 5554)
    try:
        srvr = ManagerServer(server_address, handler_class)
        print("Starting webserver...")
        srvr.serve_forever()

    except BaseException as e:
        if e:
            print e
        print("Shutting down webserver...")
        srvr.server_close()
