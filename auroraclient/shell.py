# Aurora-client Shell
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
import sys, os
from keystoneclient.v2_0 import client as ksclient
from SendJSON import JSONSender

class AuroraArgumentParser(argparse.ArgumentParser):
    
    def base_parser(self):
        parser = argparse.ArgumentParser(prog='aurora', description='Virtualization and SDI for wireless access points (SAVI Testbed)',
                                         epilog='Created by the SAVI McGill Team')
        
        subparsers = parser.add_subparsers()
        
        # Load the JSON file
        try:
            JFILE = open('json/shell.json', 'r')
            commands = json.load(JFILE)[0]
            JFILE.close()
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
            
            # Load all optional and positional arguments for the current sub arguemnt
            for osarg in subarg[2]:
                if type(osarg[0]) is list and osarg[1]['action']=='store':
                    temp_parser.add_argument(*osarg[0], action=osarg[1]['action'], nargs=osarg[1]['nargs'], default=osarg[1]['default'],
                                             choices=osarg[1]['choices'], metavar=osarg[1]['metavar'], help=osarg[1]['help'])
                
                elif type(osarg[0]) is not list and osarg[1]['action']=='store':
                    temp_parser.add_argument(osarg[0], action=osarg[1]['action'], nargs=osarg[1]['nargs'], default=osarg[1]['default'],
                                             choices=osarg[1]['choices'], metavar=osarg[1]['metavar'], help=osarg[1]['help'])
                
                elif type(osarg[0]) is list and osarg[1]['action']=='store_true':
                    temp_parser.add_argument(*osarg[0], action=osarg[1]['action'], default=osarg[1]['default'], help=osarg[1]['help'])
                                             
                else:
                    temp_parser.add_argument(osarg[0], action=osarg[1]['action'], default=osarg[1]['default'], help=osarg[1]['help'])
        
        return parser

class AuroraConsole():

    def main(self, argv):
        if(len(argv) < 2):
            print('Error! Unexpected number of arguments.')
        else:
            function = argv[1] #Used for attrs function call
            parser = AuroraArgumentParser()
            params = vars(parser.base_parser().parse_args(argv[1:]))
            #For add-slice and modify, we need to load the JSON file
            if function == "ap-slice-create" or function == "ap-slice-modify":
                if not params['file']:
                    print 'Please Specify a file argument!'
                    return
                else:
                    try:
                        JFILE = open('json/slicetemp.json', 'r')
                        fileContent = json.load(JFILE)
                        params['file'] = fileContent
                        JFILE.close()
                    except:
                        print('Error loading json file!')
                        sys.exit(-1)
            #Authenticate
            try:
                authInfo = self.authenticate()
            except:
                print 'Invalid Credentials!'
                sys.exit(-1)       
            #We will send in the following format: {function:"",parameters:""}
            toSend = {"function":function,"parameters":params}
            if toSend: #--help commands will not start the server
                JSONSender().sendJSON("http://localhost:5554", toSend)
            
        
    def _get_ksclient(self, **kwargs):
        """Get an endpoint and auth token from Keystone.
        :param username: name of user
        :param password: user's password
        :param tenant_id: unique identifier of tenant
        :param tenant_name: name of tenant
        :param auth_url: endpoint to authenticate against
        """
        return ksclient.Client(username=kwargs.get('username'),
                               password=kwargs.get('password'),
                               tenant_id=kwargs.get('tenant_id'),
                               tenant_name=kwargs.get('tenant_name'),
                               auth_url=kwargs.get('auth_url'),
                               cacert=kwargs.get('cacert'),
                               insecure=kwargs.get('insecure'))
    
    def authenticate(self):
        kwargs = {
                    'username': os.getenv('OS_USERNAME'),
                    'password': os.getenv('OS_PASSWORD'),
                    'tenant_id': os.getenv('OS_TENANT_ID'),
                    'tenant_name': os.getenv('OS_TENANT_NAME'),
                    'auth_url': os.getenv('OS_AUTH_URL'),
                    'endpoint_type': os.getenv('OS_ENDPOINT_TYPE'),
                    'cacert': os.getenv('OS_CACERT'),
                    'insecure': False,
                    'region_name': os.getenv('OS_REGION_NAME')
                }
        _ksclient = self._get_ksclient(**kwargs)
        token = _ksclient.auth_token
        return token
        
if __name__ == '__main__':
    AuroraConsole().main(sys.argv)
