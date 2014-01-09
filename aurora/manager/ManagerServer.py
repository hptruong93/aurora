# Simple Manager HTTP Server for receiving JSON files (Adapted from Micheal Smith's Code)

import BaseHTTPServer
import json
from manager import *

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    
    def __init__(self):
        #BaseHTTPRequestHandler().__init__(self)
        super(MyHandler, self).__init__()
        self.manager = Manager() #Start a manager instance
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        
        #Open response file
        RESPONSEFILE = open('json/response.json', 'r')
        response = json.load(RESPONSEFILE)
        
        self.wfile.write(response)
    
    def do_POST(self):
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        JSONfile = json.loads(data_string)
        # Begin the response
        self.send_response(200)
        self.end_headers()
        #Send to manager.py
        #Format of response: {"status":(true of false) ,"message":"string if necessary"}
        response = self.manager.parseargs(JSONfile['function'], JSONfile['parameters'], 1,1,1)
        
        #Save response to file
        RESPONSEFILE = open('json/response.json', 'w')
        json.dump(response, RESPONSEFILE, sort_keys=True, indent=4)
        RESPONSEFILE.close()
    
    # Sends a document
    def sendPage( self, type, body ):
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
        

if __name__ == "__main__":
    handler_class=MyHandler
    server_address = ('', 5554)
    try:
        srvr = BaseHTTPServer.HTTPServer(server_address, handler_class)
        print("Starting webserver...")
        srvr.serve_forever()
    except:
        print("Shutting down webserver...")
        srvr.server_close()
