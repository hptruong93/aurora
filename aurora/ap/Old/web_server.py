import BaseHTTPServer
import urlparse
import json

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.1"
    
    # Not implementing at this time
    def do_GET( self ):
        self.send_response( 501 )
    
    def do_POST( self ):
        self.log_message( "Command: %s Path: %s Headers: %r"
                          % ( self.command, self.path, self.headers.items() ) )
        # Make sure packet has data and type = JSON
        if self.headers.has_key('content-length') and self.headers.has_key('content-type') and self.headers['content-type'] == 'application/x-www-form-urlencoded':
            
            length= int( self.headers['content-length'] )
            data_received = self.process_data(self.rfile.read(length))
            response = ("You posted: " + str(data_received))
            self.sendPage("text/plain", response)
        else:
            self.send_response( 400 )
    
    
    def sendPage( self, type, body ):
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
        
        
    def process_data(self, data):
        print("To string: " + str(data))
        decoded = urlparse.parse_qs(data)
        print("Decoded: " + str(decoded))
        return decoded


if __name__ == "__main__":
    handler_class=MyHandler
    server_address = ('', 5555)
    try:
        srvr = BaseHTTPServer.HTTPServer(server_address, handler_class)
        print("Starting webserver...")
        srvr.serve_forever()
    except KeyboardInterrupt:
        srvr.server_close()
   
