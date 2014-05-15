# Veth Flavor Plugin for slice_plugin
# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

import copy
import importlib
import json
import os
import sys


class VETHPlugin(object):

    def __init__(self, tenant_id):
        self.attributes = {'attach_to':{'listable':False, 'default':None}, 'name':{'listable':False, 'default':None}}
        self.entryFormat = {'flavor':'veth', 'attributes':{}}

    def parse(self, entry, numSlice, currentIndex, entryIndex):
        parsedEntry = copy.deepcopy(self.entryFormat)
        
        #First, ensure all attributes are present
        if self.attributes.keys().sort() == entry['attributes'].keys().sort():
            #Loop through the attributes
            for key in self.attributes:
                parsedEntry['attributes'][key] = str(entry['attributes'][key])
                
        else:
            print('Error in json file, attributes do not match in veth Flavor (VirtualInterfaces)!')
            sys.exit(-1) #Maybe implement an exception?
            
        return parsedEntry
