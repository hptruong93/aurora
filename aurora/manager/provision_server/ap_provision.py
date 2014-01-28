import BaseHTTPServer
import json, os
import threading

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
                config_file = json.dumps(json.load(open('provision_server/' + file_name + '.json','r')))
                
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
        
# Outside of class - code to start/stop server

handler_class = MyHandler
server_address = ('', 5555)
server = BaseHTTPServer.HTTPServer(server_address, handler_class)

def update_reply_queue(reply_queue):
    provision_dir = "provision_server"
    paths = os.listdir(provision_dir)
    result = []
    for fname in paths:
        if fname.endswith(".json"):
            result.append(os.path.join(provision_dir, fname))
            
    for fname in result:
        with open(fname, 'r') as CONFIG_FILE:
            config = json.load(CONFIG_FILE)
        config['rabbitmq_reply_queue'] = reply_queue
        with open(fname, 'w') as CONFIG_FILE:
            json.dump(config, CONFIG_FILE, indent=4)   

def run():
    print "Starting provision server..."
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

def stop():
    print "Shutting down provision server..."
    server.shutdown()

