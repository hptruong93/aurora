# VirtualBridges Plugin for slice_plugin
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, os, copy, importlib, sys

class VirtualBridgeManager():
    
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.flavors = {'ovs':'plugins.OvsPlugin.OvsPlugin', 'linux_bridge':'plugins.LinuxBridgePlugin.LinuxBridgePlugin'}
        self.default = [{'flavor':'linux_bridge', 'attributes':{'name':'linux_bridge', 'interfaces':[], 'bridge_settings':{}, 'port_settings':{}}}]
        
    def parse(self, data, numSlice, currentIndex):
        VBridge = [[] for x in range(len(data))]
        if len(data) == 0: #Return basic default
            return self.default
        else:
            #Loop through VirtualBridges
            for (index, entry) in enumerate(data):
                if entry['flavor'] not in self.flavors:
                    print('Error! Unknown Flavor in VirtualBridges!')
                    sys.exit(-1)
                else:
                    #Load the module
                    module_name, class_name = self.flavors[entry['flavor']].rsplit(".",1)
                    newmodule = importlib.import_module(module_name) #If module is already loaded, importlib will not load it again (already implemented in importlib)
                    VBridge[index] = getattr(newmodule, class_name)(self.tenant_id).parse(entry, numSlice, currentIndex, index) #Last index represents the VBridge entry number
        
        return VBridge
