import re
import subprocess


class Monitor:

    def __init__(self, database):
        #inti motitor with database
        self.database = database

    def get_status(self):
        #get traffic information fo each ap_slice
        ap_slice_status = {}
        for slice in self.database.get_slice_list():
            if slice != "default_slice":
                slice_data = self.database.get_slice_data(slice)
                total_tx_bytes = 0
                for entry in slice_data["VirtualInterfaces"]:
                    if entry["attributes"]["attach_to"] == self.__get_interface_name(slice_data):
                        rx_bytes, tx_bytes = self.__get_network_traffic(entry["attributes"]["name"])
                        try:
                            total_tx_bytes = int(tx_bytes) + int(rx_bytes)
                        except ValueError:
                            print "Invalid Number %s" % tx_bytes
                ap_slice_status[slice] = total_tx_bytes
        return ap_slice_status

    def __get_interface_name(self, slice_data):
        for entry in slice_data["RadioInterfaces"]:
            if entry["flavor"] == "wifi_bss":
                return entry["attributes"]["if_name"]

    def __get_network_traffic(self, interface):
        #get bytes transmit by interface
        output = subprocess.Popen(['ifconfig', interface], stdout=subprocess.PIPE).communicate()[0]
        rx_bytes = re.findall('RX bytes:([0-9]*) ', output)[0]
        tx_bytes = re.findall('TX bytes:([0-9]*) ', output)[0]
        return (rx_bytes, tx_bytes)
