# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

from __future__ import division #This is not needed for python 3.x

from abc import *
import glob
import json
import sys
import traceback

import MySQLdb as mdb

from aurora.ap_provision import reader as provision_reader
from aurora.request_verification import verification_exception as exceptions
from aurora import query_agent as filter
from aurora import config

#This module is called by manager before acting on any AP.
#This will detect inconsistency/ invalid request/operation of the manager requested by the client.

GENERAL_CHECK = 'general_check'
CREATE_SLICE = 'create_slice' #This is the command name appears in the request parsed by manager.py
DELETE_SLICE = 'delete_slice' #This is the command name appears in manager.py

AP_ETH_IFACE = 'eth0'

#Base abstract class for all verifications
class RequestVerification():
    __metaclass__ = ABCMeta
    
    @staticmethod
    def ap_name_exists(physical_ap):
        ap_names = filter.query('ap', ['name'], ['name = "%s"' % physical_ap])
        if len(ap_names) != 0:
            return True
        return False

    #Do not override this
    def verify(self, command, request):
        check_result = self._detail_verification(command, request)
        if check_result:
            raise self._get_exception()(check_result)

    @classmethod
    def _get_exception(cls):
        raise NotImplemented

    @abstractmethod
    def _detail_verification(self, command, request):
        pass

class APSliceSSIDVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.DuplicatedSlice

    #If request = None, it checks for inconsistency in the database, namely an AP with n radios should not have more than 4n ap slices
    #If request != None, it checks for the ap requested for available space.
    #The method raises a NoAvailableSpaceLeftInAP exception if there is any conflict.
    def _detail_verification(self, command, request):
        try:
            if request is None:
                result = filter.query('ap_slice', ['ap_slice_ssid'], \
                                                  ['status <> "DELETED" GROUP BY ap_slice_ssid HAVING COUNT(ap_slice_ssid) > 1'])
                
                if len(result) != 0:
                    ssid_list = [str(i[0]) for i in result]
                    return "Duplicated slice exists. SSIDs are " + ", ".join(ssid_list)
            else:
                radio_interface = request['config']['RadioInterfaces']
                for entry in radio_interface:
                    if entry['flavor'] == 'wifi_bss':
                        new_ssid = entry['attributes']['name']

                result = filter.query('ap_slice', ['COUNT(ap_slice_ssid)'], ['status <> "DELETED"', \
                                                                             'tenant_id = "%s"' % request['tenant_id'],\
                                                                             'ap_slice_ssid = "%s"' % new_ssid])

                if result[0][0] != 0: #Meaning there is already a slice with "new_ssid" as ssid
                    return "Duplicated slice ssid " + str(new_ssid)
        except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
        return None

class APSliceNumberVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.NoAvailableSpaceLeftInAP

    #If request = None, it checks for inconsistency in the database, namely an AP with n radios should not have more than 4n ap slices
    #If request != None, it checks for the ap requested for available space.
    #The method raises a NoAvailableSpaceLeftInAP exception if there is any conflict.
    def _detail_verification(self, command, request):
        _ADDITIONAL_SLICE = {#For each command, we will check for a certain adding constant
            GENERAL_CHECK : 0, 
            CREATE_SLICE : 1
        }
        
        try:
            name = 0
            slice_left = 1

            if request is None:
                result = filter.query('ap', ['name', 'number_slice_free'], [])

                for ap in result:
                    if ap[slice_left] < 0:
                        return 'The AP ' + str(ap[name]) + ' has no space left to create new slice.'
            else:
                if not RequestVerification.ap_name_exists(request['physical_ap']):
                    raise exceptions.NoSuchAPExists(str(request['physical_ap']))

                result = filter.query('ap', ['name', 'number_slice_free'], ['name = "%s"' % request['physical_ap']])

                for ap in result: #We expect only 1 ap though
                    if ap[slice_left] - _ADDITIONAL_SLICE[command] < 0:
                        return 'The AP \'' + str(ap[name]) + '\' has no space left to execute command \'' + command + '\'.'
        except mdb.Error, e:
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
        except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
        return None

#See RadioConfigInvalid exception for what this class is verifying
class RadioConfigExistedVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.RadioConfigInvalid

    def _detail_verification(self, command, request):
        if request is None:
            return None
        else:
            #Check for invalid configuration on ap radio using the request
            try:
                request_ap_info = provision_reader.get_physical_ap_info(request['physical_ap'])
                configuring_radio = provision_reader.get_radio_wifi_radio(request['config'])
                request_has_config = configuring_radio is not None

                if configuring_radio is None:
                    requested_radio = provision_reader.get_radio_wifi_bss(request['config'])
                    number_slices = provision_reader.get_number_slice_on_radio(request_ap_info, requested_radio)
                else:
                    number_slices = provision_reader.get_number_slice_on_radio(request_ap_info, configuring_radio)

                if number_slices == -1:
                    raise exceptions.NoSuchAPExists(str(request['physical_ap']))

                config_existed = number_slices != 0

                if config_existed and request_has_config:
                    return "Radio for the ap " + request['physical_ap'] + " has already been configured. Cannot change the radio's configurations."
                elif (not config_existed) and (not request_has_config):
                    return "Radio for the ap " + request['physical_ap'] + " has not been configured. An initial configuration is required."

            except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
        return None

#See BridgeNumberInvalid exception for what this class is verifying
class BridgeNumberVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.BridgeNumberInvalid

    def _detail_verification(self, command, request):
        if request is None:
            return None
        else:
            try:
                bridge_list = request['config']['VirtualBridges']
                if len(bridge_list) != 1:
                    return "Attempt to create slice with " + str(len(bridge_list)) + " bridge(s). Exactly one bridge is required."
            except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))

#See VirtualInterfaceNumberInvalid exception for what this class is verifying
class VirtualInterfaceNumberVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.VirtualInterfaceNumberInvalid

    def _detail_verification(self, command, request):
        try:
            if request is None:
                return None
            else:
                #Check for number of VirtualInterface in the request
                number_of_virtual_interface = len(request['config']['VirtualInterfaces'])
                if number_of_virtual_interface != 2:
                    return "Attempt to create slice with " + str(number_of_virtual_interface) + " interface(s). Exactly two VirtualInterface is required."
            return None
        except KeyError, e:
            raise exceptions.MissingKeyInRequest(str(e.args[0]))
        
#See AccessConflict exception for what this class is verifying
#This class assumes the request has been checked with APSliceNumberVerification, BridgeNumberVerification and
#VirtualInterfaceNumberVerification
class AccessConflictVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.AccessConflict

    def _detail_verification(self, command, request):
        if request is None:
            return None
        else:
            try:
                tenant_id = request['tenant_id']

                requested_bridge = request['config']['VirtualBridges'][0]['attributes']['name']
                requested_interfaces = set([])
                for interface in request['config']['VirtualInterfaces']:
                    requested_interfaces.add(interface['attributes']['attach_to'])

                physical_ap = request['physical_ap']                    

                #Get all of his slices
                slice_list = filter.query('ap_slice', ['ap_slice_id'], ['tenant_id = "%s"' % tenant_id, \
                                                                        'physical_ap = "%s"' % physical_ap, \
                                                                        'status <> "DELETED"'])
                
                #Get the client's slices
                result = [item for sublist in slice_list for item in sublist]

                #At this point, we are sure that the ap exists since its existence has been previously checked by
                #APSliceNumberVerification
                ap_info = provision_reader.get_physical_ap_info(physical_ap)
                init_database = ap_info['last_known_config']['init_database']

                for slice in init_database:
                    if (slice not in result) and (slice != 'default_slice'): #Then slice must be someone else's
                        current_slice = init_database[slice]
                        bridge = current_slice['VirtualBridges'][0]['attributes']['name']

                        interfaces = set([])
                        for interface in current_slice['VirtualInterfaces']:
                            iface_bind = interface['attributes']['attach_to']
                            if iface_bind != AP_ETH_IFACE:
                                interfaces.add(iface_bind)

                        #Check if conflict
                        if not interfaces.isdisjoint(requested_interfaces):
                            conflict = interfaces.intersection(requested_interfaces)
                            raise exceptions.AccessConflict("Access conflict for interfaces " + ', '.join(conflict))

                        if bridge == requested_bridge:
                            raise exceptions.AccessConflict("Access conflict for bridge. Please choose another bridge.")

            except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))
            return None


#See InsufficientBandwidth exception for what this class is verifying
#This class assumes the request has been checked with APSliceNumberVerification, BridgeNumberVerification,
#VirtualInterfaceNumberVerification and AccessConflictVerification
class BandwidthVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.InsufficientBandwidth

    def _check_band_width(self, requested, number_of_slice, sum_so_far):
        MAX_BANDWIDTH = {1 : 20 * (1024 * 1024),         #20Mbps
                         2 : 14 * (1024 * 1024),
                         3 : 9 * (1024 * 1024),
                         4 : 9 * (1024 * 1024),
                         5 : 9 * (1024 * 1024),
                         6 : 9 * (1024 * 1024),
                         7 : 9 * (1024 * 1024),
                         8 : 9 * (1024 * 1024),}

        max_bandwidth = MAX_BANDWIDTH[number_of_slice + 1] #including this one as well
        max_allowance = max_bandwidth / (number_of_slice + 1) #including this one as well

        if (requested >= max_allowance) or (requested >= max_bandwidth - sum_so_far):
            return False
        return True

    def _detail_verification(self, command, request):
        try:
            if request is None:
                return None
            else:
                #Check bandwidth requested match with the supported bandwidth
                request_up = provision_reader.get_uplink(request['config']) #bps
                request_down = provision_reader.get_downlink(request['config']) #bps
                requested_radio = provision_reader.get_radio_wifi_radio(request['config'])

                ap_info = provision_reader.get_physical_ap_info(request['physical_ap'])
                number_slices = provision_reader.get_slice_count(ap_info)

                uplink = 0
                downlink = 0

                slices = provision_reader.get_slices(ap_info)

                for slice in slices:
                    radio = provision_reader.get_radio_wifi_bss(slices[slice])
                    if radio == requested_radio:
                        uplink += int(provision_reader.get_uplink(slices[slice]))
                        downlink += int(provision_reader.get_downlink(slices[slice]))

                if not self._check_band_width(request_up, number_slices, uplink):
                    return "The request uplink " + str(request_up) + " is too high!"
                elif not self._check_band_width(request_down, number_slices, downlink):
                    return "The request downlink " + str(request_down) + " is too high!"
            return None
        except KeyError, e:
                raise exceptions.MissingKeyInRequest(str(e.args[0]))

#See IllegalSliceDeletion exception for what this class is verifying
class ValidDeleteVerification(RequestVerification):
    @classmethod
    def _get_exception(cls):
        return exceptions.IllegalSliceDeletion

    def _detail_verification(self, command, request):
        try:
            if request is None:
                return None
            else:
                #Check for validity of deletion
                result = filter.query('ap_slice', ['physical_ap'], ['tenant_id = "%s"' % request['tenant_id'], \
                                                                    'ap_slice_id = "%s"' % request['slice'], \
                                                                    'status <> "DELETED"'])

                if len(result) == 0:
                    raise exceptions.NoSuchSliceExists(request['slice'])
                #There should be only one ap_name
                ap_name = [element for tupl in result for element in tupl][0]
                ap_info = provision_reader.get_physical_ap_info(ap_name)
                slice = provision_reader.get_slice(request['slice'], ap_name)
                if slice is None: #Slice is none means it has never been successfully created. The client is deleting a FAILED slice.
                    return None

                current_radio = provision_reader.get_radio_wifi_bss(slice)
                slice_count = provision_reader.get_number_slice_on_radio(ap_info, current_radio)
                if slice_count != 1: #Have to check if this is the main slice
                    if provision_reader.get_radio_interface(slice, 'wifi_radio') is not None:
                        return "Cannot delete slice containing radio configurations!"
            return None
        except mdb.Error, e:
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)
