import BaseHTTPServer
import json, os
import threading
from pprint import pprint

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
def get_json_files():
    provision_dir = "provision_server"
    paths = os.listdir(provision_dir)
    result = []
    for fname in paths:
        if fname.endswith(".json"):
            result.append(os.path.join(provision_dir, fname))
    return result

def update_reply_queue(reply_queue):
    flist = get_json_files()
    for fname in flist:
        with open(fname, 'r') as CONFIG_FILE:
            config = json.load(CONFIG_FILE)
        config['rabbitmq_reply_queue'] = reply_queue
        with open(fname, 'w') as CONFIG_FILE:
            json.dump(config, CONFIG_FILE, indent=4)   

def update_last_known_config(ap, config):
    flist = get_json_files()
    ap_config_name = None
    for fname in flist:
        F = open(fname, 'r')
        prev_config = json.load(F)
        if prev_config['queue'] == ap:
            ap_config_name = F.name
            break
    print F
    F.close()
    del F
    prev_config['default_config']['init_database'] = config
    config = prev_config
    pprint(config)
    with openf(ap_config_name, 'w') as F:
        print "Dumping config to ", F.name
        json.dump(config, F, indent=4)
        print F.name + " updated for " + ap
    
    
                
    

def run():
    print "Starting provision server..."
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

def stop():
    print "Shutting down provision server..."
    server.shutdown()

