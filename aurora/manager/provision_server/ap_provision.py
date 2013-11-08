import BaseHTTPServer
import json

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    
    def do_GET( self ):
        # Verify request type
        if self.path.startswith("/initial_ap_config_request/"):
            # Open file with name of everything after the request
            try:
                file_name = self.path[27:]
                if ".." in file_name:
                    raise Exception("File names outside directory not permitted.")
                config_file = json.dumps(json.load(open(file_name + '.json','r')))
                
            except:
                # File does not exist/ not permitted/ not json
                self.send_response(404)
            else:
                # File OK
                self.sendPage("application/json", config_file)
        # Bad request
        else:
            self.send_response( 400 )
    
    # Not implemented
    def do_POST( self ):
        self.send_response( 400 )
    
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
   
