import json
import os

#Warning: tenant_info will not be used if
#any of the following environment variable exists: AURORA_TENANT, AURORA_PROJECT, AURORA_USER
CONFIG = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/.config'))