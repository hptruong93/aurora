# Aurora Console
# SAVI Mcgill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

"""
Command-line interface to the Aurora API
"""

import argparse

class AuroraArgumentParser(argparse.ArgumentParser):
    
    def base_parser(self):
        parser = argparse.ArugmentParser(prog='aurora', description='Virtualization and SDI for wireless access points (SAVI Testbed)',
                                         epilog='Created by the SAVI McGill Team')
        
        parser.add_argument(
