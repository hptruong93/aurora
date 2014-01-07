#Adapted from Micheal Smith's provision server code
import BaseHTTPServer
import json
import threading

class MyHandler( BaseHTTPServer.BaseHTTPRequestHandler ):
    server_version= "Aurora/0.2"
    
    def do_GET( self ):
        self.send_response(400) #Not yet implemented
    
    # Not implemented
    def do_POST( self ):
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        
        JSONfile = json.loads(data_string)
        # Begin the response
        self.send_response(200)
        self.end_headers()
        
        if JSONfile['status']:
            print 'Command handled\n'
            if JSONfile['message']:
                print JSONfile['message']
        else:
            print 'Failure\n'
            if JSONfile['message']:
                print JSONfile['message']
        
    
    # Sends a document
    def sendPage( self, type, body ):
        self.send_response( 200 )
        self.send_header( "Content-type", type )
        self.send_header( "Content-length", str(len(body)) )
        self.end_headers()
        self.wfile.write( body )
        
# Outside of class - code to start/stop server

handler_class = MyHandler
server_address = ('', 5552)
server = BaseHTTPServer.HTTPServer(server_address, handler_class)
server_thread = threading
def run():

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    return server_thread

def stop(server_thread):
    server.shutdown()
    server_thread.join()
    server.server_close()
    

