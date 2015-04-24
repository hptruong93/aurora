# RESTful API for communication with the Floodlight server
# For use with ovs version >= 2.3.1

import httplib, json

class OpenFlowController:

    def __init__(self, controlHost, controlPort=8080):
        # Init floodlight for ip of machine on which floodlight is running
        self.server = controlHost
        self.port = controlPort

    def get_flow(self, switch='all'):
        # get flow(s) from the Floodlight server
        conn = httplib.HTTPConnection(self.server, self.port)
        
        # URL path that is converted into a server-side command
        path = '/wm/staticflowpusher/list/' + switch + '/json'        
        conn.request("GET", path)
        
        response = conn.getresponse()
        ret = (response.status, response.reason, response.read())
        conn.close()
        
        # print (ret[0],ret[1])
        return json.loads(ret[2])

    def add_flow_json(self, flow):
        # Pushes a premade flow to the Floodlight server

        if(flow == None or flow["name"] == None or flow["name"] == ""):
            return "Please use a valid flow or use the add_flow function to set individual parameters"
        
        ret = self.__rest_call(flow, "POST")

        if(ret[2] == 200):
            return "Successfully pushed flow"
        return "Failed to push flow"

    def add_flow(self, flowName, flowSwitch, parameters, actions):
        # Constructs a flow from arbitrary parameter values and pushes the restult to the Floodlight server
        # parameters are a list with items in the form "param=value", actions are a string (comma separated, *no spaces*)
        # e.g. add_flow("flow-1", "00:00:00:00:00:00:00:00", parameters=["priority=1","in_port=1"], actions="output=2,set_eth_dst=00:00:00:00:00:01"):
        
        if(flowName == "" or flowSwitch == ""):
            print "Please specify at least a flow name and switch"
            return
        
        flow = {
            "name":flowName,
            "switch":flowSwitch
        }
        
        for item in parameters:
            key = item.split("=",1)[0]
            value = item.split("=",1)[1]
            flow[key] = value
        
        flow["actions"] = actions
        
        ret = self.__rest_call(flow, "POST")
        
        if(ret[2] == 200):
            return "Successfully pushed flow"
        return "Failed to push flow"

    def remove_flow(self, flowName):
        # deletes flow of flow name
        ret = self.__rest_call({"name":flowName}, "DELETE")
        if(ret[2] == 200):
            return "Successfully deleted flow"
        return "Failed to delete flow"

    def __rest_call(self, data, action):
        # Performs an HTTP call to the server based on the information received
        conn = httplib.HTTPConnection(self.server, self.port)
        
        path = '/wm/staticflowpusher/json'
        body = json.dumps(data)
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
        }
        
        conn.request(action, path, body, headers)
        
        response = conn.getresponse()
        ret = (response.status, response.reason, response.read())

        conn.close()
        
        return ret
