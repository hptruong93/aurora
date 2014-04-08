# Capsulator Flavor Plugin for slice_plugin
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import copy
import glob
import importlib
import json
import os
import sys
import traceback
import types

from aurora.exc import *


class CapsulatorPlugin(object):

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.attributes = {
            'attach_to':{'listable':False, 'default':None},
            'forward_to':{'listable':False, 'default':None}, 
            'name':{'listable':False, 'default':None},
            'tunnel_tag':{'listable':True, 'default':self.default_tuntag()}, 
            'is_virtual':{'listable':False, 'default':None}
        }
        self.entryFormat = {'flavor':'capsulator', 'attributes':{}}
        
    def default_tuntag(self):
        #Load tenant slice database
        config_db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                     'config_db',
                                     str(self.tenant_id))

        ttlist = [0]
        for file_ in glob.glob(os.path.join(config_db_dir, "*.json")):
            try:
                content = json.load(open(file_, 'r'))
                for interface in content.get('VirtualInterfaces',None):
                    ttlist.append(
                        int(interface.get(
                                'attributes',{}
                            ).get(
                                'tunnel_tag', 0
                            )
                        )
                    )
            except Exception:
                traceback.print_exc(file=sys.stdout)

        return max(ttlist) + 1

    def parse(self, entry, numSlice, currentIndex, entryIndex):
        TuntagOffset = currentIndex + entryIndex #For Generation purposes, ensures a unique tuntag for each slice
        parsedEntry = copy.deepcopy(self.entryFormat)
        
        auto_tunnel_tag = False
        if entry['attributes'].get('tunnel_tag') == "auto":
            auto_tunnel_tag = True
            del entry['attributes']['tunnel_tag']

        #First, ensure all attributes that are not default are present
        for attr in self.attributes.keys():
            if self.attributes[attr]['default'] is None:
                if attr not in entry['attributes']:
                    print "Attr: %s" % attr
                    err_msg = 'Error in json file, attributes do not match in capsulator Flavor (VirtualInterfaces)!'
                    print(err_msg)
                    raise Exception(err_msg + '\n')
                  #  sys.exit(-1) #Maybe implement an exception?
            else:
                if not attr in entry['attributes']:
                    parsedEntry['attributes'][attr] = self.attributes[attr]['default']

        #print "numSlice:",numSlice
        #print entry['attributes'][key]

        # Loop through the attributes
        for key in self.attributes:
            if not key in entry['attributes']: #Default
                parsedEntry['attributes'][key] = str(self.attributes[key]['default'] + TuntagOffset)
            elif not self.attributes[key]['listable']: #Not a list, append to parsedEntry directly
                if key == 'is_virtual':
                    parsedEntry['attributes'][key] = (entry['attributes'][key])
                else:
                    parsedEntry['attributes'][key] = str(entry['attributes'][key])
            else: #List entry, check for cases
                try:
                    # Case 1, single AP
                    if numSlice == 1:
                        if type(entry['attributes'][key]) is types.IntType:
                            parsedEntry['attributes'][key] = str(entry['attributes'][key])
                        elif len(entry['attributes'][key]) == 1:
                            parsedEntry['attributes'][key] = str(entry['attributes'][key][0])
                        else:
                            raise InvalidCapsulatorConfigurationException()

                    # Case 2, multiple APs
                    elif numSlice == len(entry['attributes'][key]):
                        parsedEntry['attributes'][key] = str(entry['attributes'][key][currentIndex])
                    
                    # Case 3, Empty list, we need to generate (will need to use init loaded json information)
                    elif len(entry['attributes'][key]) == 0:
                        parsedEntry['attributes'][key] = str(self.attributes[key]['default'] + TuntagOffset)
                    
                    # Case 4, error in data
                    else:
                        print numSlice
                        print len(entry['attributes'][key])
                        err_msg = 'Error in json file, please check that the tunnel_tags match the number of APs!'
                    #    print(err_msg)
                        raise Exception(err_msg + '\n')
                  #      sys.exit(-1) #Maybe implement an exception?
                except Exception:
                    traceback.print_exc(file=sys.stdout)
            
        if auto_tunnel_tag:
            parsedEntry['attributes']['auto'] = True

        return parsedEntry
