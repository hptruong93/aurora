import re
import subprocess


class Monitor:
    """The Monitor class tracks slice data usage and access point
    hardware info, such as available memory and free disk space

    """

    def __init__(self, database):
        #inti motitor with database
        self.database = database

    def get_stats(self):
        """Fetches stats for the ap slices on this access point,
        combines it with data gathered about the memory,
        and returns both in a dictionary.

        :rtype: dict

        """
        ap_slice_stats = self._get_ap_slice_stats()
        memory_stats = self._get_memory_stats()
        return ({"ap_slice_stats":ap_slice_stats,
                 "memory_stats":memory_stats})

    def _get_memory_stats(self):
        """Fetches memory statistics from /proc/meminfo using 
        regular expressions to parse output.

        :rtype: dict

        """
        try:
            output = subprocess.check_output(['cat', '/proc/meminfo'])
            memory_mb = re.search('MemTotal: *([0-9]*) ', output).group(1)
            free_disk = re.search('MemFree: *([0-9]*) ', output).group(1)
            # Convert to MB
            (memory_mb, free_disk) = (int(memory_mb)/1000, int(free_disk)/1000)

            self.database.hw_set_memory_mb(memory_mb)
            self.database.hw_set_free_disk(free_disk)

            return {"memory_mb":memory_mb,
                    "free_disk":free_disk}
        except:
            print "[Monitor.py]: _get_memory_stats(): Something went wrong"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60

    def _get_ap_slice_stats(self):
        """Sums bytes transmitted and received for each slice,
        returns a dict containing their traffic usage.

        :rtype: dict

        """
        ap_slice_stats = {}
        for slice in self.database.get_slice_list():
            if slice != "default_slice":
                slice_data = self.database.get_slice_data(slice)
                total_tx_bytes = 0
                for entry in slice_data["VirtualInterfaces"]:
                    if entry["attributes"]["attach_to"] == self._get_interface_name(slice_data):
                        rx_bytes, tx_bytes = self._get_network_traffic(entry["attributes"]["name"])
                        try:
                            total_tx_bytes = int(tx_bytes) + int(rx_bytes)
                        except ValueError:
                            print "Invalid Number %s" % tx_bytes
                ap_slice_stats[slice] = total_tx_bytes
        return ap_slice_stats

    def _get_interface_name(self, slice_data):
        """Returns the name of the interface on the wireless
        side of a slice's virtual bridge - typically this
        interface will have a name similar to wlan0.

        :param dict slice_data: Slice configuration from database
        :rtype: string

        """
        for entry in slice_data["RadioInterfaces"]:
            if entry["flavor"] == "wifi_bss":
                return entry["attributes"]["if_name"]

    def _get_network_traffic(self, interface):
        """Finds the transmitted and received bytes for a 
        given interface.

        :param string interface:
        :rtype: tuple

        """
        output = subprocess.Popen(['ifconfig', interface], stdout=subprocess.PIPE).communicate()[0]
        rx_bytes = re.findall('RX bytes:([0-9]*) ', output)[0]
        tx_bytes = re.findall('TX bytes:([0-9]*) ', output)[0]
        return (rx_bytes, tx_bytes)
