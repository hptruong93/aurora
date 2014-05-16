# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

#Simple Client JSON Sender using POST over HTTP

import ast
import json
import time
import traceback
import os

import requests
import config

class JSONSender():
    HTTP_TIMEOUT = 15

    def send_json(self, url, payload, request_id):
        tenant_id = os.environ.get("AURORA_TENANT", config.CONFIG['tenant_info']['tenant_id'])
        project_id = os.environ.get("AURORA_PROJECT", config.CONFIG['tenant_info']['project_id'])
        user_id = os.environ.get("AURORA_USER", config.CONFIG['tenant_info']['user_id'])

        print "Tenant %s querying..." % tenant_id

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
            print 'Command sent.  ',
        else:
            print 'Unsuccessful.  Response: %s' % (r.status_code)
        
        #Sleep for 1 seconds while waiting for response
        time.sleep(1)

        try:
            r = requests.get(url, params = {'request_id': request_id}, timeout=self.HTTP_TIMEOUT)    
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
            print 'Returned message:'
        else:
            print 'Action failed:'
        #print '-'*13
        print message
        return message
        
            
if __name__ == '__main__': #FOR TESTING
    sender = JSONSender()
    FILE = open('json/apslice.json', 'r')
    payload = json.load(FILE)
    url = 'http://132.206.206.133:5554' #Will change
    sender.send_json(url, payload)
