#Simple Client JSON Sender using POST over HTTP

import requests
import json
import clientserver
import time

class JSONSender():
    
    def sendJSON(self, url, payload):
        #Start clientserver
        clientserver.run()
        
        r = requests.post(url, data=json.dumps(payload))
        print("Response: "+str(r.status_code))
        
        #Sleep for 2 seconds while waiting for response
        time.sleep(2)
        
        clientserver.stop()

if __name__ == "__main__": #FOR TESTING
    sender = JSONSender()
    FILE = open("json/apslice.json", "r")
    payload = json.load(FILE)
    url = "http://localhost:5555" #Will change
    sender.sendJSON(url, payload)
