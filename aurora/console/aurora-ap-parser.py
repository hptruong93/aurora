# Aurora AP Parser (Parses a Json File)
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Parses a JSON file for the information to send to APs
Format:{
            VirtInterfaces:[[flavor(capsulator/veth),{attributes}],[flavor(capsulator/veth),{attributes}]...],
            VirtBridges:[[flavor,{attributes}],[flavor,{attributes}]...],
            APConfig:[]
       }
"""

import json
import sys

class AuroraAPParser():

    def __init__(self):
        #Initialize all objects
        VInf = console.VirtInterfaces.VirtInterfaces()
        VBridge = console.VirtBridges.VirtBridges()
        APConf = console.APConfig.APConfig()
        try:
            JFILE = open('ap.json', 'r')
            commands = json.load(JFILE)
        except:
            print('Error loading json file!')
            sys.exit(-1)

    def parse(self):
        # Load all VirtInterfaces (pass each one individually)
        for interfaces in commands['VirtInterfaces']:
            VInf.create(interfaces[0], interfaces[1])
        
        #Load all VirtBridges (pass each one individually)
        for bridges in commands['VirtBridges']:
            VBridge.create(bridges[0], bridges[1])
        
        #Load all APConfigs
        for configs in commands['APConfig']:
            APConf.create(configs[0], configs[1])
            
