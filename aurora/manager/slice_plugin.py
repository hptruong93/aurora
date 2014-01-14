# Slice Plugins: For parsing VirtualInterfaces, VirtualBridges, and RadioInterfaces
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, os, copy, importlib, sys

class SlicePlugin():
    
    def __init__(self, tenant_id, user_id, tag=None):
        #To add later: RadioInterfaces
        self.plugins = {'VirtualInterfaces':'plugins.VirtualInterfaceManager.VirtualInterfaceManager',
                        'VirtualBridges':'plugins.VirtualBridgeManager.VirtualBridgeManager'}
        
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tag = None
        if tag:
            self.tag = tag
        
    def parseCreateSlice(self, data, numSlice, json_list):
        #Loop through values in plugin
        for key in self.plugins:
            if key in data:
                #Load the module
                module_name, class_name = self.plugins[key].rsplit(".",1)
                newmodule = importlib.import_module(module_name) #If module is already loaded, importlib will not load it again (already implemented in importlib)
                for i in range(numSlice): #loop through slice configs
                    json_list[i][key] = getattr(newmodule, class_name)(self.tenant_id).parse(data[key], numSlice, i) #i is the current index
           
            else: #Make default
                print(key+' not found. File might not parse correctly. Please check configuration and try again!')
                
        #Add wrapper around json_list and return
        return self.addCreateSliceWrapper(json_list, self.tag, self.user_id)
                
    def addCreateSliceWrapper(self, json_list, tag, user_id):
        """This method takes a json_list and puts each entry in the correct format (i.e. user, slice, command, config)
        for sending to the APs"""
        newlist = []
        for entry in json_list:
            tempdata = {}
            tempdata['config'] = entry
            tempdata['user'] = user_id
            tempdata['slice'] = tag[0]
            tempdata['command'] = 'create_slice'
            newlist.append(tempdata)     
        return newlist
