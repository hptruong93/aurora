# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#
"""This module is responsible for building the configuration JSON 
which will be dispatched to the aurora agent.

Slice Plugins: For parsing VirtualInterfaces, 
VirtualBridges, and RadioInterfaces

"""
import copy
import importlib
import json
import logging
import os
import sys
import traceback

from aurora.cls_logger import get_cls_logger

LOGGER = logging.getLogger(__name__)


class SlicePlugin(object):
    """Slice plugin class responsible for splitting and parsing slice 
    configurations if the configuration target is multiple access 
    points.

    """
    def __init__(self, tenant_id, user_id, tag=None):
        #To add later: RadioInterfaces
        self.LOGGER = get_cls_logger(self)
        self.plugins = {
            'VirtualInterfaces':'aurora.plugins.vif_plugin.VirtualInterfacePlugin',
            'VirtualBridges':'aurora.plugins.vbr_plugin.VirtualBridgePlugin'
        }
        
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tag = None
        if tag:
            self.tag = tag
        
    def parse_create_slice(self, data, numSlice, json_list):
        """Parses the sections in ``self.plugins`` from the 
        configuration JSON passed in ``data``.  Uses the modules in 
        aurora.plugins.

        :param dict data: Data for a slice passed from client
        :param int numSlice: Number of slices in this create command
        :param list json_list: List outline for parsed data
        :returns: list of JSON configurations to be dispatched

        """
        #Loop through values in plugin
        for key in self.plugins:
            if key in data:
                #Load the module
                module_name, class_name = self.plugins[key].rsplit(".",1)
                newmodule = importlib.import_module(module_name) #If module is already loaded, importlib will not load it again (already implemented in importlib)
                for i in range(numSlice): #loop through slice configs
                    try:
                        json_list[i][key] = getattr(newmodule, class_name)(self.tenant_id).parse(data[key], numSlice, i) #i is the current index
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        raise Exception(e.message)
            else: #Make default
                self.LOGGER.warning(key+' not found. File might not parse correctly. Please check configuration and try again!')
                
        #Add wrapper around json_list and return
        return self._add_create_slice_wrapper(json_list, self.tag, self.tenant_id)
                
    def _add_create_slice_wrapper(self, json_list, tag, tenant_id):
        """This method takes a json_list and puts each entry in 
        the correct format (i.e. user, slice, command, config) for 
        sending to the APs.

        :param list json_list: List of configuration jsons
        :param str tag: Warning -- let this parameter be assigned by
            :func:`ap_slice_create \
                <aurora.manager.Manager.ap_slice_create>`
        :param str tenant_id: Tenant ID for the slice
        :returns: list of JSON configurations to be dispatched

        """
        newlist = []
        for entry in json_list:
            tempdata = {}
            tempdata['config'] = entry
            tempdata['user'] = tenant_id
            tempdata['slice'] = tag
            tempdata['command'] = 'create_slice'
            newlist.append(tempdata)     
        return newlist