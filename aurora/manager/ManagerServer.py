# Simple Manager HTTP Server for receiving JSON files (Adapted from Micheal Smith's Code)

import BaseHTTPServer
import json

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    
    def do_GET(self):
        self.send_response(400) #Not yet implemented
    
    def do_POST(self):
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))

        # Begin the response
        self.send_response(200)
        self.end_headers()
        
        JSONfile = json.loads(data_string)
        
        print JSONfile
        
    
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
