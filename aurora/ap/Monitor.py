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
            slice_data = self.database.get_slice_data(slice)
            total_tx_bytes = 0
            for entry in slice_data["VirtualInterfaces"]:
                tx_bytes = self.__get_network_traffic(entry["attributes"]["name"])
                try:
                    total_tx_bytes += int(tx_bytes)
                except ValueError:
                    print "Invalid Number %s" % tx_bytes
            ap_slice_status[slice] = total_tx_bytes
        return ap_slice_status

    def __get_network_traffic(self, interface):
        #get bytes transmit by interface
        output = subprocess.Popen(['ifconfig', interface], stdout=subprocess.PIPE).communicate()[0]
        tx_bytes = re.findall('TX bytes:([0-9]*) ', output)[0]
        return tx_bytes
