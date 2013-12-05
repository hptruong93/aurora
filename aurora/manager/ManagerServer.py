# Simple Manager HTTP Server for receiving JSON files (Adapted from Micheal Smith's Code)

import BaseHTTPServer
import json
from manager import *
import requests

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    
    def do_GET(self):
        self.send_response(400) #Not yet implemented
    
    def do_POST(self):
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        JSONfile = json.loads(data_string)
        # Begin the response
        self.send_response(200)
        self.end_headers()
        #Send to manager.py
        #Format of response: {"status":(true of false) ,"message":"string if necessary"}
        print JSONfile['function']
        print JSONfile['parameters']
        response = Manager().parseargs(JSONfile['function'], JSONfile['parameters'], 1,1,1)
        
        #Send response back to client
        r = requests.post("http://localhost:5552", data=json.dumps(response))
        print("Response: "+str(r.status_code))
    
    # Sends a document
    def sendPage( self, type, body ):
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
        

if __name__ == "__main__":
    handler_class=MyHandler
    server_address = ('', 5555)
    try:
        srvr = BaseHTTPServer.HTTPServer(server_address, handler_class)
        print("Starting webserver...")
        srvr.serve_forever()
    except KeyboardInterrupt:
        srvr.server_close()
