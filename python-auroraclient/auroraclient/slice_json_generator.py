#LOCATION TAGS IN AP_SLICE
# Aurora JSON Generator (Generates a Json File)
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json
import sys
import ast
import os

from auroraclient import json_sender #Enable the communication between manager and generator

CLIENT_DIR = os.path.dirname(os.path.abspath(__file__)) # detect the local directory

class SliceJsonGenerator():
    
    def __init__(self, filename, sliceID, tenantID, projectID):
        #Initialize outside dictionary and populate
        self.data = {}
        self.params = {}
        #self.data['ap_slice_id'] = sliceID
        #self.data['tenant_id'] = tenantID
        #self.data['project_id'] = projectID
        #self.data['VirtualInterfaces'] = []
        #self.data['VirtualBridges'] = []
        #self.data['RadioInterfaces'] = [] #For future use?
        
        self.params['data'] = []
        self.params['type'] = []
        #Initialize function dictionary
        self.options = {1:self.SliceConfig, 2:self.addVI, 3:self.listVI, 4:self.delVI, 5:self.addVB, 6:self.listVB, 7:self.delVB, 8:self.printConfig}
        self.generate(filename)
    
    def generate(self, filename):
        exitLoop = False
        while not exitLoop:
            print('Choose an option: ')
            print('1. General Slice Configuration')
            print('2. Add a Virtual Interface')
            print('3. List Virtual Interfaces')
            print('4. Delete a Virtual Interface')
            print('5. Add a Virtual Bridge')
            print('6. List Virtual Bridges')
            print('7. Delete a Virtual Bridge')
            print('8. Print Complete Configuration')
            print('9. Finish WITHOUT Generating Json')
            print('0. Finish and Generate Json')
            choice = raw_input()
            if choice == '9':
                exitLoop = True
            elif choice == '0':
                exitLoop = True
                # Dump to JSON file
                try:
                    print "the file name is " + filename
                    self.JFILE = open(filename, "w")
                except IOError:
                    print('Error opening file for writing!')
                    sys.exit(-1)
                json.dump(self.data['config'], self.JFILE, sort_keys=True, indent=4)
                self.JFILE.flush()
                self.JFILE.close()
            else:
                try:
                    self.options[int(choice)]()
                except (KeyError, ValueError, IndexError):
                    print('Please enter a valid option!')
                    
            
    def SliceConfig(self):
        Loop = False
        
        try:
           ## print "the file name is " + filename
            self.JFILE = open(os.path.join(CLIENT_DIR, 'json/template.json'), "r")
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        self.data['config'] = json.load(self.JFILE)
        self.JFILE.close()
        
        #print file_content['VirtualWIFI'][0]['attributes'];
        #print file_content['VirtualWIFI'][1]['attributes'];
        #print file_content['VirtualBridges'];
        #print file_content['VirtualInterfaces'];
        
        print('Enter attributes...')
        print('SSID NAME:')
        while(not Loop):
            tmp_data = raw_input()
            Loop = self.communicatewithManager(tmp_data,'SSID_NAME')
        self.data['config']['VirtualWIFI'][1]['attributes']['name'] = tmp_data
        
        Loop = False
        print('Bridge Type:')
        while(not Loop):
            tmp_data = raw_input()
            Loop = self.communicatewithManager(tmp_data,'bridge_type')
        self.data['config']['VirtualBridges'][0]['flavor'] = tmp_data
        
        self.data['physical_ap'] = 'openflow1'
        self.data['tenant_id'] = os.environ.get("AURORA_TENANT", -1)
        print self.data
        if(self.communicatewithManager(self.data,'radio_check')):
            del self.data['config']['VirtualWIFI'][0]
        del self.data['physical_ap']
        del self.data['tenant_id']

        #print('firmware:')
        #while(not Loop):
            #self.data['firmware'] = raw_input()
            #Loop = self.communicatewithManager(self.data['firmware'],'firmware')
        #Loop = False
        
        #print('slice_qos_priority:')
        #while(not Loop):
            #self.data['slice_qos_priority'] = raw_input()
            #Loop = self.communicatewithManager(self.data['slice_qos_priority'],'slice_qos_priority')
        #Loop = False
        
        #print('slice_qos_aggregate_rate:')
        #while(not Loop):
        #    self.data['slice_qos_aggregate_rate'] = raw_input()
        #    Loop = self.communicatewithManager(self.data['slice_qos_aggregate_rate'],'slice_qos_aggregate_rate')
        
    def communicatewithManager(self, data, Ftype): # Implement a channel to communicate with manager
        print Ftype
        self.params['data'] = data
        self.params['type'] = Ftype
        toSend = {
            'function':'configuration-generation',
            'parameters':self.params,
            'tenant_id':os.environ.get("AURORA_TENANT", -1),
            'project_id':os.environ.get("AURORA_PROJECT", -1),
            'user_id':os.environ.get("AURORA_USER", -1),
        }
        if toSend: #--help commands will not start the server
            response = json_sender.JSONSender().send_json('http://localhost:5554', toSend) # change back to 132.206.206.133:5554
        if 'true' not in response:
            print " Please Enter the right value!!"
            return False
        else:
            return True
            
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
                print('tunnel_tag:')
                entry['attributes']['tunnel_tag'] = raw_input()
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
            
            if(flavor == 'ovs' or flavor == 'linux_bridge'):
                validFlavor = True
                entry = {'flavor':str(flavor), 'attributes':{}}
                
                print('Enter attributes...')
                print('name:')
                entry['attributes']['name'] = raw_input()
                print('interfaces (separate each interface by a space):')
                entry['attributes']['interfaces'] = str(raw_input()).split()
                print('bridge_settings (Enter a dictionary: {"key1":"value1", "key2":"value2"...}):')
                try:
                    entry['attributes']['tunnel_tag'] = ast.literal_eval(str(raw_input()))
                except SyntaxError:
                    print("Invalid Syntax. Please check and try again!")
                    return
                print('port_settings (Enter a dictionary of dictionaries: {"port1:{"key1":"value1", "key2":"value2"...},"port2":..."}):')
                try:
                    entry['attributes']['isVirtual'] = ast.literal_eval(str(raw_input()))
                except SyntaxError:
                    print("Invalid Syntax. Please check and try again!")
                    return
            
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

def main():
    slicegenerate = SliceJsonGenerator(os.path.join(CLIENT_DIR, 'json/yangwutest.json'),1,1,1) # Initialize the slice_json_generator

if __name__ == '__main__':
    main()
