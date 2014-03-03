import os, sys, glob, traceback
import json
import logging

#This module provides an API to read ap_provision

#Get all physical_ap
def _get_physical_ap_info():
    output = {}
    current_dir = os.getcwd()
    provision_dir = os.path.dirname(os.path.abspath(__file__)) #Change if file is moved somewhere else
    os.chdir(provision_dir)
    for file in glob.glob("*.json"):
        content = json.load(open(file))
        output[content['queue']] = content
    os.chdir(current_dir)
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

def get_rate_up(slice):
    sum_up = 0
    for item in slice['TrafficAttributes']:
        sum_up += int(item['attributes']['rate_up'])
    return sum_up

def get_rate_down(slice):
    sum_down = 0
    for item in slice['TrafficAttributes']:
        sum_down += int(item['attributes']['rate_down'])
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


if __name__ == '__main__':
    print get_number_slice_on_radio('openflow1', 'radio0')
