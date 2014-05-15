# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#
""".. warning::

    Out of date and unused!  Use at own risk.

Module for generating a JSON configuration.  To be compatible with 
Aurora Manager v0.2 and later, follow the structure of this functional
JSON configuration::

    {
        "VirtualWIFI": [
            {
                "flavor" : "wifi_radio",
                "attributes" : 
                    {
                        "name" : "radio0",
                        "channel" : "1",
                        "txpower" : "20",
                        "disabled" : "0",
                        "country" : "CA",
                        "hwmode" : "abg"   
                    }
            },
            {
                "flavor" : "wifi_bss",
                "attributes" : 
                    {
                        "name" : "NetworkSSID",
                        "radio" : "radio0",
                        "if_name" : "wlan0",
                        "encryption_type":"wep-open",
                        "key":"00000"
                    }
            }
        ], 
        "VirtualBridges": [
            {
                "flavor":"linux_bridge",
                "attributes":   
                    {
                        "name":"linux-br",
                        "interfaces":
                            ["vwlan0","tun0"],
                        "bridge_settings":{},
                        "port_settings":{}
                    }
            }
        ], 
        "VirtualInterfaces": [
            {
                "flavor":"capsulator",
                "attributes": 
                    {
                        "attach_to":"eth0",
                        "name":"tun0",
                        "forward_to":"10.0.0.1",
                        "tunnel_tag":"auto",
                        "is_virtual":true
                    }
            },
            {
                "flavor":"veth",
                "attributes": 
                    {
                        "attach_to":"wlan0",
                        "name":"vwlan0",
                        "mac":"00:00:00:00:00:01"
                    }
            }
        ]
    }

"""
import ast
import json
import sys

class SliceJSONGenerator(object):
    
    def __init__(self, filename):
        #Initialize outside dictionary and populate
        self.data = {}
        self.data['VirtualInterfaces'] = []
        self.data['VirtualBridges'] = []
        self.data['VirtualWIFI'] = [] #For future use?
        #Initialize function dictionary
        self.options = {1:self.addVI, 2:self.listVI, 3:self.delVI, 4:self.addVB, 5:self.listVB, 6:self.delVB, 7:self.printConfig}
        self.generate(filename)
    
    def generate(self, filename):
        exitLoop = False
        while not exitLoop:
            print('Choose an option: ')
            print('1. Add a Virtual Interface')
            print('2. List Virtual Interfaces')
            print('3. Delete a Virtual Interface')
            print('4. Add a Virtual Bridge')
            print('5. List Virtual Bridges')
            print('6. Delete a Virtual Bridge')
            print('7. Print Complete Configuration')
            print('8. Finish WITHOUT Generating Json')
            print('0. Finish and Generate Json')
            choice = raw_input()
            if choice == '8':
                exitLoop = True
            elif choice == '0':
                exitLoop = True
                # Dump to JSON file
                try:
                    self.JFILE = open(filename, 'w')
                except IOError:
                    print('Error opening file for writing!')
                    sys.exit(-1)
                json.dump(self.data, self.JFILE, sort_keys=True, indent=4)
                self.JFILE.flush()
                self.JFILE.close()
            else:
                try:
                    self.options[int(choice)]()
                except (KeyError, ValueError, IndexError):
                    print('Please enter a valid option!')
            
    def addVI(self):
        validFlavor = False
        while not validFlavor:
            print('Enter a flavor (capsulator or veth): ')
            flavor = raw_input()
            
            if(flavor == 'capsulator'):
                validFlavor = True
                entry = {'flavor':'capsulator', 'attributes':{}}
                
                print('Enter attributes...')
                print('attach_to:')
                entry['attributes']['attach_to'] = raw_input()
                print('forward_to:')
                entry['attributes']['forward_to'] = raw_input()
                print('name:')
                entry['attributes']['name'] = raw_input()
                print('list of tunnel_tag (enter a tunnel_tag for each AP, for multiple tags, separate by a space, leave blank for auto generation):')
                entry['attributes']['tunnel_tag'] = str(raw_input()).split() #TEMPORARY FIELD: will be removed when sending to APs
                print('isVirtual:')
                entry['attributes']['isVirtual'] = raw_input()
            
            elif(flavor == 'veth'):
                validFlavor = True
                entry = {'flavor':'veth', 'attributes':{}}
                
                print('Enter attributes...')
                print('attach_to:')
                entry['attributes']['attach_to'] = raw_input()
                print('name:')
                entry['attributes']['name'] = raw_input()
            
            else:
                print('Please choose a valid flavor!')
         
        self.data['VirtualInterfaces'].append(entry)
        print('Virtual Interface Saved!')
    
    def listVI(self):
        if len(self.data['VirtualInterfaces']) == 0:
            print('\nNo Virtual Interfaces!\n')
        else:
            for index in range(0, len(self.data['VirtualInterfaces'])):
                print('Index '+str(index)+':')
                print self.data['VirtualInterfaces'][index]
    
    def delVI(self):
        self.listVI()
        print('Enter an index to delete: ')
        choice = raw_input()
        try:
            del self.data['VirtualInterfaces'][int(choice)]
        except (KeyError, IndexError):
            print('Please choose a valid index!')
        else:
            print('Entry Deleted!')
    
    def addVB(self):
        validFlavor = False
        while not validFlavor:
            print('Enter a flavor (ovs or linux_bridge): ')
            flavor = raw_input()
            
            if flavor == 'ovs':
                validFlavor = True
                entry = {'flavor':'ovs', 'attributes':{}}
                entry['attributes']['bridge_settings'] = {}
                entry['attributes']['port_settings'] = {}
                
                print('Enter attributes...')
                print('name:')
                entry['attributes']['name'] = raw_input()
                print('interfaces (separate each interface by a space):')
                entry['attributes']['interfaces'] = str(raw_input()).split()
                print('bridge_settings: controller (enter a controller for each AP, for multiple controllers, separate by a space, leave blank for auto generation):')
                entry['attributes']['bridge_settings']['controller'] = str(raw_input()).split()
                print('bridge_settings: dpid (enter a dpid for each AP, for multiple DPIDs, separate by a space, leave blank for auto generation):')
                entry['attributes']['bridge_settings']['dpid'] = str(raw_input()).split()
                print('additional bridge_settings (Enter a dictionary: {"key1":"value1", "key2":"value2"...}):')
                try:
                    entry['attributes']['bridge_settings'] = ast.literal_eval(str(raw_input()))
                except SyntaxError:
                    print("Nothing added to bridge_settings (if this is not what you wanted, please check your syntax and try again).")
                print('port_settings (Enter a dictionary of dictionaries: {"port1:{"key1":"value1", "key2":"value2"...},"port2":..."}):')
                try:
                    entry['attributes']['port_settings'] = ast.literal_eval(str(raw_input()))
                except SyntaxError:
                    print("Nothing added to port_settings (if this is not what you wanted, please check your syntax and try again).")
                    entry['attributes']['port_settings'] = {}
            
            elif flavor == 'linux_bridge':
                validFlavor = True
                entry = {'flavor':'linux_bridge', 'attributes':{}}
                entry['attributes']['bridge_settings'] = {}
                entry['attributes']['port_settings'] = {}
                print('Enter attributes...')
                print('name:')
                entry['attributes']['name'] = raw_input()
                print('interfaces (separate each interface by a space):')
                entry['attributes']['interfaces'] = str(raw_input()).split()
                print('bridge_settings (Enter a dictionary: {"key1":"value1", "key2":"value2"...}):')
                try:
                    entry['attributes']['bridge_settings'] = ast.literal_eval(str(raw_input()))
                except SyntaxError:
                    print("Invalid Syntax. Nothing added to bridge_settings!")
                print('port_settings (Enter a dictionary of dictionaries: {"port1:{"key1":"value1", "key2":"value2"...},"port2":..."}):')
                try:
                    entry['attributes']['port_settings'] = ast.literal_eval(str(raw_input()))
                except SyntaxError:
                    print("Invalid Syntax. Nothing added to port_settings!")
                    entry['attributes']['port_settings'] = {}
                    
            else:
                print('Please choose a valid flavor!')
         
        self.data['VirtualBridges'].append(entry)
        print('Virtual Bridge Saved!')
    
    def listVB(self):
        if len(self.data['VirtualBridges']) == 0:
            print('\nNo Virtual Bridges!\n')
        else:
            for index in range(0, len(self.data['VirtualBridges'])):
                print('Index '+str(index)+':')
                print self.data['VirtualBridges'][index]
        
    def delVB(self):
        self.listVB()
        print('Enter an index to delete: ')
        choice = raw_input()
        try:
            del self.data['VirtualBridges'][int(choice)]
        except (KeyError, IndexError):
            print('Please choose a valid index!')
        else:
            print('Entry Deleted!')
            
    def printConfig(self):
        print(json.dumps(self.data, sort_keys=True, indent=4))

if __name__ == '__main__':
    SliceJSONGenerator('core/json/slicetemp.json')
