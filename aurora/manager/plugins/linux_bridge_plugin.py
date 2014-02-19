# Linux Bridge Flavor Plugin for slice_plugin
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import copy
import importlib
import json
import os
import sys


class LinuxBridgePlugin(object):

    def __init__(self, tenant_id):
        self.attributes = {
            'name':{'listable':False, 'default':None}, 
            'interfaces':{'listable':False, 'default':None}, 
            'port_settings':{'listable':False, 'default':None}, 
            'bridge_settings':{'listable':False, 'default':None}
        }
        self.sub_attributes = {}
        self.entryFormat = {'flavor':'linux_bridge', 'attributes':{}}

    def parse(self, entry, numSlice, currentIndex, entryIndex):
        parsedEntry = copy.deepcopy(self.entryFormat)
        
        #First, ensure all attributes are present
        if self.attributes.keys().sort() == entry['attributes'].keys().sort():
            #Loop through the attributes
            for key in self.attributes:
                #parsedEntry['attributes'][key] = str(entry['attributes'][key])
                parsedEntry['attributes'][key] = entry['attributes'][key]
                
        else:
            print('Error in json file, attributes do not match in linux_bridge Flavor (VirtualBridges)!')
            sys.exit(-1) #Maybe implement an exception?
            
        return parsedEntry
