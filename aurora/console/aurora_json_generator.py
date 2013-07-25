# Aurora JSON Generator (Generates a Json File)
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json
import sys

class AuroraJsonGenerator():
    
    def __init__(self, filename):
        #Initialize outside dictionary and populate
        self.data = {}
        self.data['VirtInterfaces'] = []
        self.data['VirtBridges'] = []
        self.data['APConfig'] = []
        #Initialize function dictionary
        self.options = {1:self.addVI, 2:self.listVI, 3:self.delVI, 4:self.addVB, 5:self.listVB, 6:self.delVB,
                   7:self.addAP, 8:self.listAP, 9:self.delAP}
        try:
            self.JFILE = open(filename, 'w')
        except IOError:
            print('Error opening file for writing!')
            sys.exit(-1)
        self.generate()
    
    def generate(self):
        exitLoop = False
        while not exitLoop:
            print('Choose an option: ')
            print('1. Add a Virtual Interface')
            print('2. List Virtual Interfaces')
            print('3. Delete a Virtual Interface')
            print('4. Add a Virtual Bridge')
            print('5. List Virtual Bridges')
            print('6. Delete a Virtual Bridge')
            print('7. Add an Access Point Configuration')
            print('8. List Access Point Configurations')
            print('9. Delete an Access Point Configuration')
            print('0. Finish and Generate Json')
            choice = raw_input()
            if choice == '0':
                exitLoop = True
                # Dump to JSON file
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
                entry = ['capsulator',{}]
                
                print('Enter attributes...')
                print('attach_to:')
                entry[1]['attach_to'] = raw_input()
                print('forward_to:')
                entry[1]['forward_to'] = raw_input()
                print('name:')
                entry[1]['name'] = raw_input()
                print('tunnel_tag:')
                entry[1]['tunnel_tag'] = raw_input()
                print('isVirtual:')
                entry[1]['isVirtual'] = raw_input()
            
            elif(flavor == 'veth'):
                validFlavor = True
                entry = ['veth', {}]
                
                print('Enter attributes...')
                print('attach_to:')
                entry[1]['attach_to'] = raw_input()
                print('name:')
                entry[1]['name'] = raw_input()
            
            else:
                print('Please choose a valid flavor!')
         
        self.data['VirtInterfaces'].append(entry)
        print('Virtual Interface Saved!')
    
    def listVI(self):
        for index in range(0, len(self.data['VirtInterfaces'])):
            print('Index '+str(index)+':')
            print self.data['VirtInterfaces'][index]
    
    def delVI(self):
        self.listVI()
        print('Enter an index to delete: ')
        choice = raw_input()
        try:
            del self.data['VirtInterfaces'][int(choice)]
        except (KeyError, IndexError):
            print('Please choose a valid index!')
        else:
            print('Entry Deleted!')
    
    def addVB(self):
        validFlavor = False
        while not validFlavor:
            print('Enter a flavor (ovs or linux_bridge): ')
            flavor = raw_input()
            
            if(flavor == 'ovs'):
                validFlavor = True
                entry = ['ovs',{}]
                
                print('Enter attributes...')
                print('placeholder:')
                entry[1]['placeholder'] = raw_input()
            
            elif(flavor == 'linux_bridge'):
                validFlavor = True
                entry = ['linux_bridge', {}]
                
                print('Enter attributes...')
                print('placeholder:')
                entry[1]['placeholder'] = raw_input()
            
            else:
                print('Please choose a valid flavor!')
         
        self.data['VirtBridges'].append(entry)
        print('Virtual Bridge Saved!')
    
    def listVB(self):
        for index in range(0, len(self.data['VirtBridges'])):
            print('Index '+str(index)+':')
            print self.data['VirtBridges'][index]
        
    def delVB(self):
        self.listVB()
        print('Enter an index to delete: ')
        choice = raw_input()
        try:
            del self.data['VirtBridges'][int(choice)]
        except (KeyError, IndexError):
            print('Please choose a valid index!')
        else:
            print('Entry Deleted!')
    
    def addAP(self):
        validFlavor = False
        while not validFlavor:
            print('Enter a flavor (openwrt or debian): ')
            flavor = raw_input()
            
            if(flavor == 'openwrt'):
                validFlavor = True
                entry = ['openwrt',{}]
                
                print('Enter attributes...')
                print('placeholder:')
                entry[1]['placeholder'] = raw_input()
            
            elif(flavor == 'debian'):
                validFlavor = True
                entry = ['debian', {}]
                
                print('Enter attributes...')
                print('placeholder:')
                entry[1]['placeholder'] = raw_input()
            
            else:
                print('Please choose a valid flavor!')
                
        self.data['APConfig'].append(entry)
        print('Access Point Configuration Saved!')
    
    def listAP(self):
        for index in range(0, len(self.data['APConfig'])):
            print('Index '+str(index)+':')
            print self.data['APConfig'][index]
    
    def delAP(self):
        self.listAP()
        print('Enter an index to delete: ')
        choice = raw_input()
        try:
            del self.data['APConfig'][int(choice)]
        except (KeyError, IndexError):
            print('Please choose a valid index!')
        else:
            print('Entry Deleted!')

AuroraJsonGenerator('generated.json')
