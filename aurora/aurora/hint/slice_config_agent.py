import sys
import traceback

import re
import json
from aurora import query_agent as query
from aurora.ap_provision import reader as provision_reader

def _remove_digits(input_string):
    return ''.join([i for i in input_string if not i.isdigit()])

def _remove_letters(input_string):
    return re.sub("[^0-9]", "", input_string)

def _remove_all_symbols(input_string):
    return ''.join(e for e in input_string if e.isalnum())

def _retain_only_leters(input_string):
    return _remove_digits(_remove_all_symbols(input_string))

def _retain_only_numbers(input_string):
    return _remove_letters(_remove_all_symbols(input_string))

def hint_radio(ap_name):
    ap_info = provision_reader.get_physical_ap_info(ap_name)
    number_radio = int(ap_info['last_known_config']['init_hardware_database']['wifi_radio']['number_radio'])
    if number_radio == 2:
        radios = ["radio0", "radio1"]
    else:
        radios = ["radio0"]

    for radio in radios:
        if provision_reader.get_number_slice_on_radio(ap_info, radio) < 4:
            return radio
    return None

def hint_radio_config(ap_name, radio_name):
    ap_info = provision_reader.get_physical_ap_info(ap_name)
    number_slice = provision_reader.get_number_slice_on_radio(ap_info, radio_name)
    if number_slice > 0:
        return None
    else:
        return {
                "attributes": {
                    "disabled": "0", 
                    "name": radio_name, 
                    "country": "CA", 
                    "txpower": "20", 
                    "hwmode": "abg", 
                    "channel": "2"
                }, 
                "flavor": "wifi_radio"
                }

class InterfaceHint():

    BRIDGES = ['linux-br', 'ovs']

    def __init__(self, ap_name, interface):
        self.slices_info = provision_reader.get_slices(provision_reader.get_physical_ap_info(ap_name))
        self.interface = _remove_digits(interface)
        if self.interface[-1] == '-':
            self.interface = self.interfaces[:-1]

    def change_interface(self, new_interface):
        self.interfaces = new_interface

    def change_ap(self, new_ap):
        self.slices_info = provision_reader.get_slices(provision_reader.get_physical_ap_info(new_ap))

    def hint(self, radio_name):
        if self.interface not in self.BRIDGES:
            radio_number = _remove_letters(radio_name)
            if "veth" in self.interface: #veth does not depends on the radio number
                radio_number = 0
            full_interface = self.interface + str(radio_number)
        else:
            full_interface = self.interface

        #Start counting how many interfaces are there
        found_base_interface = False
        max = 0
        stripped_interface = _remove_all_symbols(full_interface)
        for slice in self.slices_info:
            for finding in re.findall(full_interface + "..", str(self.slices_info[slice])):
                finding = _remove_all_symbols(finding)
                if len(finding) == len(stripped_interface):
                    found_base_interface = True
                    continue

                try: 
                    if int(finding[-1]) > max:
                        max = int(finding[-1])
                except:
                    pass
        
        max += 1
        if not found_base_interface:
            return full_interface
        else:
            return  full_interface + "-%s" % max

class ConfigHint():
    def __init__(self, config):
        self.config = config

    def _change_wifi_interface(self, new_interface_name):
        old_interface_name = ""
        for radio_interface in self.config['RadioInterfaces']:
            if radio_interface['flavor'] == 'wifi_bss':
                old_interface_name = radio_interface['attributes']['if_name']

        self.config = json.loads(re.compile(old_interface_name).sub(new_interface_name, json.dumps(self.config)))

    def _change_virtual_interface(self, attachment, new_name):
        old_name = self._get_interface(attachment)['attributes']['name']
        self.config = json.loads(re.compile(old_name).sub(new_name, json.dumps(self.config)))

    def _change_radio(self, new_radio):
        old_radio = provision_reader.get_radio_wifi_bss(self.config)
        old_radio_number = _retain_only_numbers(old_radio)
        new_radio_number = _retain_only_numbers(new_radio)

        replaced = re.compile(old_radio).sub(new_radio, json.dumps(self.config))
        replaced = re.compile("wlan%s" % old_radio_number).sub("wlan%s" % new_radio_number, replaced)
        self.config = json.loads(replaced)

    def _get_interface(self, attachment):
        for interface in self.config['VirtualInterfaces']:
            if attachment in interface['attributes']['attach_to']:
                return interface
        return None

    def _change_bridge_name(self, new_bridge_name):
        self.config['VirtualBridges'][0]['attributes']['name'] = new_bridge_name

    def hint(self, ap_name):
        suggested_radio = hint_radio(ap_name)
        self._change_radio(suggested_radio)
        
        current_bridge_name = self.config['VirtualBridges'][0]['attributes']['name']
        current_bridge_name = re.compile("-[0-9]+$").sub("", current_bridge_name)
        bridge_hint = InterfaceHint(ap_name, current_bridge_name)
        self._change_bridge_name(bridge_hint.hint(suggested_radio))

        wlan_hint = InterfaceHint(ap_name, "wlan")
        self._change_wifi_interface(wlan_hint.hint(suggested_radio))

        eth_interface = self._get_interface("eth")['attributes']['name']
        
        eth_interface = _retain_only_leters(eth_interface) + "0"
        eth_hint = InterfaceHint(ap_name, eth_interface)
        self._change_virtual_interface("eth", eth_hint.hint(suggested_radio))

        radio_config = hint_radio_config(ap_name, suggested_radio)
        if radio_config is None:
            for i in xrange(len(self.config['RadioInterfaces'])):
                interface = self.config['RadioInterfaces'][i]
                if interface['flavor'] == 'wifi_radio':
                    del self.config['RadioInterfaces'][i]
                    break
        else:
            current_config = provision_reader.get_radio_wifi_radio(self.config)
            if not current_config:
                self.config['RadioInterfaces'].append(radio_config)
        return self.config
    

if __name__ == "__main__":
    print re.compile("-[0-9]+$").sub("", "vswitch-br")