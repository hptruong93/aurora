#Simple Client JSON Sender using POST over HTTP

import ast
import json
import time
import traceback

import requests

class JSONSender():
    HTTP_TIMEOUT = 10

    def send_json(self, url, payload):
        
        try:
            r = requests.post(url, data=json.dumps(payload), timeout=self.HTTP_TIMEOUT)
        except KeyboardInterrupt:
            return
        except requests.Timeout as t:
            print t.message
            return
        except:
            traceback.print_exc()
            return

        if r.status_code == 200:
            print 'Command sent.'
        else:
            print 'Unsuccessful.  Response: %s' % (r.status_code)
        
        #Sleep for 1 seconds while waiting for response
        time.sleep(1)

        try:
            r = requests.get(url, timeout=self.HTTP_TIMEOUT)    
        except KeyboardInterrupt:
            return
        except requests.Timeout as t:
            print t.message
            return
        except:
            traceback.print_exc()
            return

        dict_response = ast.literal_eval(r.text)
        message = dict_response['message']
        status = dict_response['status']
        if status:
            print 'Returned message'
        else:
            print 'Action failed'
        print '-'*13
        print message
        return message
        
            
if __name__ == '__main__': #FOR TESTING
    sender = JSONSender()
    FILE = open('json/apslice.json', 'r')
    payload = json.load(FILE)
    url = 'http://localhost:5553' #Will change
    sender.send_json(url, payload)
