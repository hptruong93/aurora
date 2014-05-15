# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#

import glob
import json
import logging
import os
import sys
import traceback

#This module provides an API to read ap_provision

#Get all physical_ap
def _get_physical_ap_info():
    output = {}
    current_dir = os.getcwd()
    provision_json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'json') #Change if file is moved somewhere else
    for file in glob.glob(os.path.join(provision_json_dir, "*.json")):
        content = json.load(open(file))
        output[content['queue']] = content
    return output

def get_physical_ap_info(physical_ap):
    try:
        return _get_physical_ap_info()[physical_ap]
    except KeyError, e:
        return None

#Return a dictionary containing all information about a slice, given what physical_ap the slice is in
#Return None if nothing is found
def get_slice(slice_id, physical_ap):
    ap = get_physical_ap_info(physical_ap)
    for slice in ap['last_known_config']['init_database']:
        if slice_id == slice:
            return ap['last_known_config']['init_database'][slice]
    return None

#Return a dictionary containing all information about all slices in a certain ap
def get_slices(ap_info):
    output = ap_info['last_known_config']['init_database']
    output.pop("default_slice", None)

    return output

#Get how many slice there are in the current ap
def get_slice_count(physical_ap_info):
    return len(physical_ap_info['last_known_config']['init_database']) - 1

#Get the radio interface given the flavor
#Return None if no interface with flavor exists
def get_radio_interface(slice, flavor):
    for interface in slice['RadioInterfaces']:
        if interface['flavor'] == flavor:
            return interface['attributes']
    return None

def get_radio_wifi_bss(slice):
    interface = get_radio_interface(slice, 'wifi_bss')
    if interface is not None:
        return interface['radio']
    return None

def get_radio_wifi_radio(slice):
    interface = get_radio_interface(slice, 'wifi_radio')
    if interface is not None:
        return interface['name']
    return None

def link_rate_to_int(rate):
    if rate.endswith('kbit'):
        rate = rate.split('kbit')[0]
        rate = int(rate) * 1024
    elif rate.endswith('mbit'):
        rate = rate.split('mbit')[0]
        rate = int(rate) * (1024**2)
    # TODO: Add others
    return int(rate)

def get_uplink(slice):
    sum_up = 0
    try:
        for item in slice['TrafficAttributes']:
            sum_up += link_rate_to_int(item['attributes']['uplink'])
    except KeyError as e:
        #Well this slice does not have any traffic info associated with it
        pass
    return sum_up

def get_downlink(slice):
    sum_down = 0
    try:
        for item in slice['TrafficAttributes']:
            sum_down += link_rate_to_int(item['attributes']['downlink'])
    except KeyError as e:
        #Well this slice does not have any traffic info associated with it
        pass
    return sum_down    

#Radio name: radio0, radio1, ... radio10
def _get_radio_number(radio_name):
    return int(radio_name[len('radio')])

def get_number_slice_on_radio(physical_ap_info, radio_name):
    slices = physical_ap_info['last_known_config']['init_database']
    count = 0

    for slice in slices:
        try:
            if get_radio_wifi_bss(slices[slice]) == radio_name:
                count += 1
        except TypeError, e: #There's a default one that is not compatible
            continue
    return count

#For testing only
if __name__ == '__main__':
    print get_number_slice_on_radio('openflow1', 'radio0')