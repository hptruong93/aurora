#Simple Client JSON Sender using POST over HTTP

import requests
import json
import time
import ast

class JSONSender():
    
    def sendJSON(self, url, payload):
        
        try:
            r = requests.post(url, data=json.dumps(payload))
            
            print("Response: "+str(r.status_code))
            
            #Sleep for 2 seconds while waiting for response
            time.sleep(2)
            
        except requests.exceptions.ConnectionError, e:
            print "Error:", e
        
        finally:
            #Be nice and let server know we're done
            clientserver.stop(s)

        r = requests.get(url)
        dictresponse = ast.literal_eval(r.text)
        message = dictresponse['message']
        status = dictresponse['status']
        print status
        print message

if __name__ == "__main__": #FOR TESTING
    sender = JSONSender()
    FILE = open("json/apslice.json", "r")
    payload = json.load(FILE)
    url = "http://localhost:5553" #Will change
    sender.sendJSON(url, payload)
