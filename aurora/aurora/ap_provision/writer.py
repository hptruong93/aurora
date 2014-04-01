import json
import logging
import os
from pprint import pformat

LOGGER = logging.getLogger(__name__)


def get_json_files():
    provision_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json')
    paths = os.listdir(provision_dir)
    result = []
    for fname in paths:
        if fname.endswith(".json"):
            result.append(os.path.join(provision_dir, fname))
    return result

def update_reply_queue(reply_queue):
    flist = get_json_files()
    for fname in flist:
        with open(fname, 'r') as CONFIG_FILE:
            config = json.load(CONFIG_FILE)
        config['rabbitmq_reply_queue'] = reply_queue
        with open(fname, 'w') as CONFIG_FILE:
            json.dump(config, CONFIG_FILE, indent=4)   

def update_last_known_config(ap, config):
    flist = get_json_files()
    ap_config_name = None
    for fname in flist:
        F = open(fname, 'r')
        prev_config = json.load(F)
        if prev_config['queue'] == ap:
            ap_config_name = F.name
            break
    try:
        LOGGER.debug(F)
    except UnboundLocalError:
        LOGGER.warn("WARNING: No accessible files in ap_provision")
    F.close()
    del F
    prev_config['last_known_config'] = config
    config = prev_config
    #LOGGER.debug(json.dumps(config, indent=4))
    print ap_config_name
    with open(ap_config_name, 'w') as F:
        json.dump(config, F, indent=4)
        LOGGER.info("%s updated for %s", F.name, ap)