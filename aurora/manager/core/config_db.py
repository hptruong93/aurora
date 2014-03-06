#!/usr/bin/python -tt
import json
import logging
import os
import string
import sys
import traceback
from types import *

from exc import *

LOGGER = logging.getLogger(__name__)
DB_FOLDER = "core/config_db/"

def save_config(config, tenant_id):
    """Saves a given configuration file in the name of it's slice
    ID within the folder for a specific tenant.

    :param dict config:
    :param int tenant_id:
    :rtype: None
    :raises NoSliceIDInConfiguration:

    """
    LOGGER.debug("Saving config.")
    assert type(config) is DictType
    try:
        ap_slice_id=config['slice']
    except KeyError:
        raise NoSliceIDInConfiguration()
    dir_path = get_file_path(ap_slice_id, tenant_id, dir_only=True)
    if not os.path.exists(dir_path):
        self.LOGGER.debug("Path %s doesn't exist, creating...", dir_path)
        try:
            os.makedirs(dir_path)
        except os.error:
            traceback.print_exc(file=sys.stdout)
            raise CannotCreateTenantConfigDir(dir_path=dir_path)
    file_path = get_file_path(ap_slice_id, tenant_id)
    with open(file_path, 'w') as CONFIG_FILE:
        LOGGER.debug("File: %s", CONFIG_FILE.name)
        json.dump(config, CONFIG_FILE, indent=4)

def modify_config(ap_slice_id, config, tenant_id):
    """Replaces part of an existing configuration file with
    the given config parameter.

    :param str ap_slice_id:
    :param dict config:
    :param int tenant_id:
    :raises ModifyConfigNotImplemented:

    """
    raise ModifyConfigNotImplemented()

def delete_config(ap_slice_id, tenant_id):
    """Deletes a configuration file from the DB.

    :param str ap_slice_id:
    :param int tenant_id:
    :rtype: None
    :raises NoConfigExistsError: if no config file to delete

    """
    file_path = get_file_path(ap_slice_id, tenant_id)
    try:
        os.remove(file_path)
    except OSError:
        raise NoConfigExistsError(slice=ap_slice_id)

def get_config(ap_slice_id, tenant_id):
    """Fetches a configuration file for the given ap_slice_id
    if one exists.

    :param str ap_slice_id: ID of the slice config to fetch
    :param int tenant_id:
    :rtype: dict
    :raises NoConfigExistsError: if no config file to delete

    """
    file_path = get_file_path(ap_slice_id, tenant_id)
    try:
        with open(file_path, 'r') as CONFIG_FILE:
            return json.load(CONFIG_FILE)
    except IOError:
        raise NoConfigExistsError(slice=ap_slice_id)

def get_file_path(ap_slice_id, tenant_id, dir_only=False):
    """Returns a relative file path where config file for related
    ap_slice_id should be kept.

    :param str ap_slice_id:
    :param int tenant_id:
    :rtype: str

    """
    if dir_only:
        return DB_FOLDER + str(tenant_id)
    return DB_FOLDER + '{0}/{1}.json'.format(tenant_id, ap_slice_id)