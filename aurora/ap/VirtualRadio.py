# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import subprocess, os, exception
# TODO: Remove when done testing
import Database

####
# Implementation note: there are two 'databases', so to speak.
# The first is in the Database class, the second
# is UCI.  While this is redundant and inefficient,
# the only other possible implementation would be to use UCI
# as a database, which would make the Database class OpenWRT-specific.
# This is not something I wish to have - it's bad enough the radio
# is specific to OpenWRT.

class VirtualRadio:
    """Responsible for configuring the WiFi radio interfaces of a device.
    This version is OpenWRT specific.  For other distributions or OSes,
    replace this class with one that implements the same functions
    as appropriate for that distro or OS."""

    WIRELESS_FILE_PATH = "/etc/config/wireless"

    def __init__(self, database):
        self.database = database
        self.setup()
        
    def setup(self):
        # Prepare radio - UCI configuration file setup
        # First, remove wireless configuration file; ignore errors
        try:
            os.remove(self.WIRELESS_FILE_PATH)
        except Exception:
            pass
            
        # Bring down any existing wifi
        subprocess.call(["wifi","down"])
        
        # Regenerate it.  We rely on wifi detect, especially
        # since it can detect the MAC address & number of radios
        detect = subprocess.check_output(["wifi","detect"])
        
        # Add package name to string, since UCI needs it
        detect2 = "package wireless\n" + detect
        
        # Call UCI, import the data (UCI automatically commits)
        uci_process = subprocess.Popen(["uci","import"],stdin=subprocess.PIPE)
        uci_process.communicate(input=detect2)
        
        
        # Count # radios
        # Each device has 1 wifi-device section
        num_radios = detect2.split().count("wifi-device")
        
        # Set # radios in database
        self.database.hw_set_num_radio(num_radios)
        self.database.hw_set_num_radio_free(num_radios)
        
        # For each radio, set up the database
        for count in range(0, num_radios):
            radio_data = {"name":"radio" + str(count), "if_name":"wlan" + str(count), "bss_list":[] }
            radio_data["channel"] = self.__radio_get_command(count, "channel")
            radio_data["hwmode"] = self.__radio_get_command(count, "hwmode")
            # Disabled should be stored as a number, not a string
            radio_data["disabled"] = int(self.__radio_get_command(count, "disabled"))
            self.database.hw_add_radio_entry(radio_data)
            
            # Delete default BSS; there will be as many as the # of 
            # radios, so we can do it here
            self.__uci_delete_bss_complete(count)
            
            
    def setup_radio(self, radio, disabled=0, channel=None, hwmode=None, txpower=None ):
        """Sets up a radio with the given parameters.  If parameters
        are unspecified, existing parameters are left unchanged.
        By default, it will enable the radio interface."""
        
        radio_entry = self.database.hw_get_radio_entry(radio)
        radio_num = radio.lstrip("radio")
        current_disabled = radio_entry["disabled"]
        
        # If the command is to disable and not currently disabled
        # We increment the number of free radios
        if disabled:
            if not current_disabled:
                self.database.hw_set_num_radio_free(self.database.hw_get_num_radio_free()+1)
                
        # Opposite situation
        else:
            if current_disabled:
                self.database.hw_set_num_radio_free(self.database.hw_get_num_radio_free()-1)
        
        # Write to database and UCI
        radio_entry["disabled"] = disabled
        self.__radio_set_command(radio_num, "disabled", disabled)
                
        if channel != None:
            self.__radio_set_command(radio_num, "channel", channel)
            radio_entry["channel"] = channel
            
        if (hwmode != None):
            self.__radio_set_command(radio_num, "hwmode", hwmode)
            radio_entry["hwmode"] = hwmode
            
        if (txpower != None):
            self.__radio_set_command(radio_num, "txpower", txpower)
            radio_entry["txpower"] = txpower
    
    
    def apply_changes(self):
        
    
    def __radio_set_command(self, radio_num, command, value):
        # We str() value, radio and command in case they are not strings (i.e. int)
        subprocess.check_call(["uci","set","wireless.radio" + str(radio_num) + "." + str(command) + "=" +str(value)])
        
    def __radio_get_command(self, radio_num, command):
        return subprocess.check_output(["uci","get","wireless.radio" + str(radio_num) + "." + str(command)])
        
    def __bss_set_command(self, bss_num, command, value):
        subprocess.check_call(["uci","set","wireless.@wifi-iface[" + str(bss_num) + "]." + str(command) + "=" +str(value)])
        
    def __bss_get_command(self, bss_num, command):
        return subprocess.check_output(["uci","get","wireless.@wifi-iface[" + str(bss_num) + "]." + str(command)])
    
    def __uci_delete_bss(self, bss_num, section):
        subprocess.call(["uci","delete","wireless.@wifi-iface[" + str(bss_num) + "]." + str(section)])
        
    def __uci_delete_bss_complete(self, bss_num):
        subprocess.call(["uci","delete","wireless.@wifi-iface[" + str(bss_num) + "]"])
    
    def __uci_delete_radio(self, radio_num, section):
        subprocess.call(["uci","delete","wireless.radio" + str(radio_num) + "." + str(section)])
        
    def __uci_add_wireless_section(self, section):
        subprocess.call(["uci","add","wireless",str(section)])
    
    def remove_radio(self, config):
        # Removes a radio interface and all associated bss
        pass
    
    def add_bss(self, radio, ssid, encryption_type=None, key=None, auth_server=None, auth_port=1812, auth_secret=None, auth_cache=0, acct_server=None, acct_port=1813, acct_secret=None,nasid=None,dae_client=None,dae_port=3799,dae_secret=None):
        """Creates a new BSS attached to the specified radio.  By default,
        there is no encryption.  Use the encryption_type and key values to set up.
        Passphrases must follow encryptions requirements (i.e. WPA/WEP require
        specific passphrase lengths)
        
        Possible encryption types include wep, psk (WPA-PSK) and psk2 (WPA-PSK2).
        These require the key field to be a passphrase which must conform 
        to WEP/WPA requirements (i.e. wpa has a minimum length).  
        
        The encryption_type may also be set to wpa or wpa2, which will
        enable the use of WPA-Enterprise using TKIP or CCMP as ciphers,
        respectively.  Enterprise security requires some options; see
        http://wiki.openwrt.org/doc/uci/wireless for details.  Generally,
        you will need at least an auth_server and auth_secret.
        """
        
        # Get associated radio and check for existing BSS
        radio_entry = self.database.hw_get_radio_entry(radio)
        radio_num = radio_entry["name"].lstrip("radio")
        total_bss = len(radio_entry["bss_list"])
        
        if total_bss >= 4:
            raise exception.ReachedBSSLimitOnRadio("The BSS limit of 4 has been reached on " + radio)
        
        main_bss = False
        if total_bss == 0:
            main_bss = True
        
        # Insert into UCI
        if main_bss:
            # We create BSS, naming them for our reference
            self.__uci_add_wireless_section("wifi-iface")
            
        
        # Use Heming's modified hostapd
        else:
            
        
    def remove_bss(self, bss):
        # Removes a bss from a radio
        pass
        
    
data = Database.Database()
test = VirtualRadio(data)
