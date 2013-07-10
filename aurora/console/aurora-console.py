# Aurora Console
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Command-line interface to the Aurora API
"""

import argparse

class AuroraArgumentParser(argparse.ArgumentParser):
    
    def base_parser(self):
        parser = argparse.ArgumentParser(prog='aurora', description='Virtualization and SDI for wireless access points (SAVI Testbed)',
                                         epilog='Created by the SAVI McGill Team')
        
        subparsers = parser.add_subparsers()
        
        subparser_ap_list = subparsers.add_parser('ap-list', help='Show a list of all Access Points')
        subparser_ap_list.add_argument('ap-list', nargs='*')
        
        subparser_ap_show = subparsers.add_parser('ap-show', help='Show a specific Access Point')
        subparser_ap_show.add_argument('ap-show', nargs='*')
        
        subparser_ap_slice_create = subparsers.add_parser('ap-slice-create', help='Create a slice')
        subparser_ap_slice_create.add_argument('ap-slice-create', nargs='*')
        
        subparser_ap_slice_delete = subparsers.add_parser('ap-slice-delete', help='Delete a slice')
        subparser_ap_slice_delete.add_argument('ap-slice-delete', nargs='*')

        subparser_ap_slice_list = subparsers.add_parser('ap-slice-list', help='Show a list of all slices')
        subparser_ap_slice_list.add_argument('ap-slice-list', nargs='*')

        subparser_ap_slice_show = subparsers.add_parser('ap-slice-show', help='Show a specific slice')
        subparser_ap_slice_show.add_argument('ap-slice-show', nargs='*')
        
        subparser_wnet_create = subparsers.add_parser('wnet-create', help='Create a Wireless Network')
        subparser_wnet_create.add_argument('wnet-create', nargs='*')
        
        subparser_wnet_delete = subparsers.add_parser('wnet-delete', help='Delete a Wireless Network')
        subparser_wnet_delete.add_argument('wnet-delete', nargs='*')
        
        subparser_wnet_join = subparsers.add_parser('wnet-join', help='Join Wireless Networks')
        subparser_wnet_join.add_argument('wnet-join', nargs='*')
        
        subparser_wnet_list = subparsers.add_parser('wnet-list', help='List all Wireless Networks')
        subparser_wnet_list.add_argument('wnet-list', nargs='*')
        
        subparser_wnet_show = subparsers.add_parser('wnet-show', help='Show a specific Wireless Network')
        subparser_wnet_show.add_argument('wnet-show', nargs='*')
        
        return parser
        
        
test = AuroraArgumentParser()
print(test.base_parser().parse_args(['wnet-create', 'beast', 'hi']))
print(test.base_parser().parse_args(['wnet-list', 'yo', 'what']))
print(test.base_parser().parse_args(['wnet-delete', 'hey', 'ciao']))
print(test.base_parser().parse_args(['wnet-show', 'good', 'day']))
print(test.base_parser().parse_args(['wnet-join', 'haha', 'gaga']))
print(test.base_parser().parse_args(['ap-show', 'bad', 'luck']))
