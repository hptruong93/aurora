# Aurora Console
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Command-line interface to the Aurora API
Uses a JSON file for commands
Format:[
         {
          optional:[[oarg1, {attributes}],[oarg2, {attributes}]...], 
          positional:[[parg1, {attributes}], [parg2, {attributes}]...], 
          subargument:[[subarg1, {attributes}, [[osarg1, {attributes}], [osarg2, {attributes}]]], [subarg2, {attributes}]...]
         }
       ]
"""

import argparse
import json
import sys

class AuroraArgumentParser(argparse.ArgumentParser):
    
    def base_parser(self):
        parser = argparse.ArgumentParser(prog='aurora', description='Virtualization and SDI for wireless access points (SAVI Testbed)',
                                         epilog='Created by the SAVI McGill Team')
        
        subparsers = parser.add_subparsers()
        
        # Load the JSON file
        try:
            JFILE = open('console.json', 'r')
            JFILE.seek(0)
            commands = json.load(JFILE)[0]
        except:
            print('Error loading json file!')
            sys.exit(-1)
        
        # Load all optional arguments
        for oarg in commands['optional']:
            parser.add_argument(oarg[0], action=oarg[1]['action'], nargs=oarg[1]['nargs'], default=oarg[1]['default'],
                                choices=oarg[1]['choices'], metavar=oarg[1]['metavar'], help=oarg[1]['help'])
                                
        
        # Load all positional arguments
        for parg in commands['positional']:
            parser.add_argument(parg[0], action=parg[1]['action'], nargs=parg[1]['nargs'], default=parg[1]['default'],
                                choices=parg[1]['choices'], metavar=parg[1]['metavar'], help=parg[1]['help'])
                                
       
        # Load all sub arguments
        for subarg in commands['subargument']:
            temp_parser = subparsers.add_parser(subarg[0], help=subarg[1]['help'])
            temp_parser.add_argument(subarg[0], action=subarg[1]['action'], nargs=subarg[1]['nargs'], default=subarg[1]['default'],
                                     choices=subarg[1]['choices'], metavar=subarg[1]['metavar'])
            
            # Load all optional arguments for the current sub arguemnt
            for osarg in subarg[2]:
                temp_parser.add_argument(osarg[0], action=osarg[1]['action'], nargs=osarg[1]['nargs'], default=osarg[1]['default'],
                                         choices=osarg[1]['choices'], metavar=osarg[1]['metavar'], help=osarg[1]['help'])
        
        return parser
        
        
test = AuroraArgumentParser()
#print(test.base_parser().parse_args(['-h']))
print(test.base_parser().parse_args(['wnet-create', 'beast', 'hi']))
print(test.base_parser().parse_args(['wnet-list', 'yo', 'what']))
print(test.base_parser().parse_args(['wnet-delete', 'hey', 'ciao']))
print(test.base_parser().parse_args(['wnet-show', 'good', 'day']))
print(test.base_parser().parse_args(['wnet-join', 'haha', 'gaga']))
print(test.base_parser().parse_args(['ap-show', 'bad', 'luck']))
