# Capsulator Flavor Plugin for slice_plugin
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, os, copy, importlib, sys

class CapsulatorPlugin():

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
        try:
            JFILE = open(os.path.dirname(__file__) + '/../json/apslice-'+str(self.tenant_id)+'.json', 'r')
            APlist = json.load(JFILE)
            JFILE.close()
        except IOError:
            print('Error opening file!')
            sys.exit(-1)
        
        #Get starting tunnel_tag numbers, for generation
        ttlist = [0]
        for entry in APlist:
            for interface in entry['VirtualInterfaces']:
                if 'tunnel_tag' in interface['attributes']:
                    ttlist.append(int(interface['attributes']['tunnel_tag']))
        return max(ttlist) + 1

    def parse(self, entry, numSlice, currentIndex, entryIndex):
        TuntagOffset = currentIndex + entryIndex #For Generation purposes, ensures a unique tuntag for each slice
        parsedEntry = copy.deepcopy(self.entryFormat)
        
        #First, ensure all attributes that are not default are present
        for attr in self.attributes.keys():
            if not self.attributes[attr]['default']:
                if not attr in entry['attributes']:
                    print('Error in json file, attributes do not match in capsulator Flavor (VirtualInterfaces)!')
                    sys.exit(-1) #Maybe implement an exception?
            else:
                if not attr in entry['attributes']:
                    parsedEntry['attributes'][attr] = self.attributes[attr]['default']
        
        print "numSlice:",numSlice
  #      print entry['attributes'][key]
                     
        #Loop through the attributes
        for key in self.attributes:
            if not key in entry['attributes']: #Default
                parsedEntry['attributes'][key] = str(self.attributes[key]['default'] + TuntagOffset)
            elif not self.attributes[key]['listable']: #Not a list, append to parsedEntry directly
                if key == 'is_virtual':
                    parsedEntry['attributes'][key] = (entry['attributes'][key])
                else:
                    parsedEntry['attributes'][key] = str(entry['attributes'][key])
            else: #List entry, check for cases
                #Case 1, single AP
                if numSlice == 1 and len(entry['attributes'][key]) == 1:
                    parsedEntry['attributes'][key] = str(entry['attributes'][key][0])
            
                #Case 2, multiple APs
                elif numSlice == len(entry['attributes'][key]):
                    parsedEntry['attributes'][key] = str(entry['attributes'][key][currentIndex])
                
                #Case 3, Empty list, we need to generate (will need to use init loaded json information)
                elif len(entry['attributes'][key]) == 0:
                    parsedEntry['attributes'][key] = str(self.attributes[key]['default'] + TuntagOffset)
                
                #Case 4, error in data
                else:
                    print numSlice
                    print len(entry['attributes'][key])
                    print('Error in json file, please check that the tunnel_tags match the number of APs!')
                    sys.exit(-1) #Maybe implement an exception?
            
        return parsedEntry
