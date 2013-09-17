# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import subprocess, os, exception
import psutil

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
        self.change_pending = {}
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
            self.__uci_delete_bss_index(count)
            
            
    def setup_radio(self, radio, disabled=0, channel=None, hwmode=None, txpower=None, country=None):
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
                self.change_pending[radio] = True
                
        # Opposite situation
        else:
            if current_disabled:
                self.database.hw_set_num_radio_free(self.database.hw_get_num_radio_free()-1)
                self.change_pending[radio] = True
        
        # Write to database and UCI
        radio_entry["disabled"] = disabled
        self.__radio_set_command(radio_num, "disabled", disabled)
                
        if channel != None:
            self.__radio_set_command(radio_num, "channel", channel)
            radio_entry["channel"] = channel
            self.change_pending[radio] = True
            
        if hwmode != None:
            self.__radio_set_command(radio_num, "hwmode", hwmode)
            radio_entry["hwmode"] = hwmode
            self.change_pending[radio] = True
            
        if txpower != None:
            self.__radio_set_command(radio_num, "txpower", txpower)
            radio_entry["txpower"] = txpower
            self.change_pending[radio] = True
        
        if country != None:
            self.__radio_set_command(radio_num, "country", country)
            radio_entry["country"] = country
            self.change_pending[radio] = True
    
    
    def apply_changes(self):
        """Resets and applies changes on any radios that require it, such as a 
        channel change or a modification of the main BSS.
        An exception will be raised with debugging information 
        if the changes are not appliedand a hostapd instance has failed. 
        Otherwise, basic information from hostapd is returned.
        
        If there are no changes to apply, the above hostapd check with
        the possible raised exception will still run."""
        
        # If there are no changes pending, commit will do nothing
        # All other code ensures change_pending is set when a commit
        # is needed, so this should be fine
        subprocess.call(["uci","commit"])
        
        # If no radios require changes, this will be empty
        for radio in self.change_pending:
            subprocess.call(["wifi", "down", str(radio)])
            subprocess.call(["wifi","up",str(radio)])
            
        self.change_pending.clear()
        
        # Make sure hostapd still running
        # # of hostapd instance = # of radios
        num_hostapd = 0
        for process in psutil.process_iter():
            if process.name == "hostapd":
                num_hostapd = num_hostapd + 1
        
        num_radios_in_use = self.database.hw_get_num_radio() - self.database.hw_get_num_radio_free()
        if num_hostapd != num_radios_in_use:
            raise exception.hostapdError("There should be " + str(num_radios_in_use) + " hostapd instances running; there are only " + str(num_hostapd) + " instead.")
    
    def __radio_set_command(self, radio_num, command, value):
        # We str() value, radio and command in case they are not strings (i.e. int)
        subprocess.check_call(["uci","set","wireless.radio" + str(radio_num) + "." + str(command) + "=" +str(value)])
        
    def __radio_get_command(self, radio_num, command):
        # rstrip is used to remove newlines from UCI
        return subprocess.check_output(["uci","get","wireless.radio" + str(radio_num) + "." + str(command)]).rstrip()
        
    def __generic_set_command(self, section, command, value):
        subprocess.check_call(["uci","set", "wireless." + str(section) + "." + str(command) + "=" +str(value)])
        
    def __create_new_section(self, section_type, name):
        subprocess.check_call(["uci","set", "wireless." + str(name) + "=" +str(section_type)])
        
    def __generic_get_command(self, section, command):
        return subprocess.check_output(["uci","get","wireless." + str(section) + "." + str(command)]).rstrip()
    
    def __uci_delete_section_name(self, section):
        subprocess.call(["uci","delete","wireless." + str(section)])
        
    def __uci_delete_bss_index(self, bss_num):
        subprocess.call(["uci","delete","wireless.@wifi-iface[" + str(bss_num) + "]"])
    
    def __uci_delete_radio(self, radio_num, section):
        subprocess.call(["uci","delete","wireless.radio" + str(radio_num) + "." + str(section)])
        
    def __uci_add_wireless_section(self, section):
        subprocess.call(["uci","add","wireless",str(section)])
    
    def add_bss(self, radio, ssid, encryption_type=None, key=None, auth_server=None, auth_port=None, auth_secret=None, acct_server=None, acct_port=None, acct_secret=None,nasid=None):
        """Creates a new BSS attached to the specified radio.  By default,
        there is no encryption.  Use the encryption_type and key values to set up.
        Passphrases must follow encryptions requirements (i.e. WPA/WEP require
        specific passphrase lengths)
        
        Possible encryption types include wep, psk (WPA-PSK) and psk2 (WPA-PSK2).
        These require the key field to be a passphrase which must conform 
        to WEP/WPA requirements (i.e. wpa has a minimum length).
        64 character WPA keys are treated as hex.  
        
        The encryption_type may also be set to wpa or wpa2, which will
        enable the use of WPA-Enterprise using TKIP or CCMP as ciphers,
        respectively.  Enterprise security requires some options; see
        http://wiki.openwrt.org/doc/uci/wireless for details.  Generally,
        you will need at least an auth_server and auth_secret.
        """
        
        # Get associated radio and number of bss's
        radio_entry = self.database.hw_get_radio_entry(radio)
        radio_num = radio_entry["name"].lstrip("radio")
        bss_list = radio_entry["bss_list"]
        total_bss = len(radio_entry["bss_list"])
        
        # Check for exising BSS with same name
        for bss in bss_list:
            if bss["ssid"] == ssid:
                raise exception.InvalidSSID("SSID " + ssid + " is already in use.")
        
        if total_bss >= 4:
            raise exception.ReachedBSSLimitOnRadio("The BSS limit of 4 has been reached on " + radio)
        
        main_bss = False
        if total_bss == 0:
            main_bss = True
        
        # Create (future) database entry
        bss_entry ={}
        
        # Insert into UCI
        if main_bss:
            
            # We create BSS, naming them for our reference
            # Name: BSS + radio num, i.e. BSS3 for radio3
            section_name = "BSS" + radio_num
            self.__create_new_section("wifi-iface", section_name)
            # Mark BSS as being main
            bss_entry["main"] = True
            
            try:
                if ssid == None or ssid == '':
                    raise exception.InvalidSSID()
                
                if encryption_type == None:
                    # Variable that determines how encryption is set
                    # 0 for none, 1 for personal, 2 for enterprise
                    encryption_category = 0
                
                else:
                    # Must be encryption, run validity checks
                    if encryption_type == "psk2" or encryption_type == "psk":
                        encryption_category = 1
                        if key == None:
                            raise exception.InvalidKey("Key must be specified.")
                        if len(key) < 8:
                            raise exception.InvalidKey("Key must be at least 8 characters long")
                        if len(key) > 64:
                            raise exception.InvalidKey("Key cannot be more that 64 characters long.")
                        
                    elif encryption_type == "wep":
                        encryption_category = 1
                        if key == None:
                            raise exception.InvalidKey("Key must be specified.")
                        try:
                            int(key, 16)
                        # If key is not Hex
                        except ValueError:
                            # Length must be either 5 or 13
                            if len(key) != 5 and len(key) != 13:
                                raise exception.InvalidKey("Key must be 5 or 13 characters.")
                        # Key is hex
                        else:
                            if len(key) != 10 and len(key) != 26:
                                raise exception.InvalidKey("Key must be 10 or 26 digits.")
                    elif encryption_type == "wpa" or encryption_type == "wpa2":
                        encryption_category = 2
                        # What enterprise allows varies wildly depending on the setup; we can't check here
                        # The user will have to check himself
            except:
                # Clean up
                self.__uci_delete_section_name(section_name)
                # Pass along exception back to user (eventually)
                raise
            else:
                self.change_pending[radio] = True
                # Checks passed, set encryption
                if encryption_category == 0:
                    self.__generic_set_command(section_name, "encryption", "none")
                    bss_entry["encryption"] = "none"
                elif encryption_category == 1:
                    self.__generic_set_command(section_name, "encryption", encryption_type)
                    self.__generic_set_command(section_name, "key", key)
                    bss_entry["encryption"] = encryption_type
                    bss_entry["key"] = key
                elif encryption_category == 2:
                    self.__generic_set_command(section_name, "encryption", encryption_type)
                    bss_entry["encryption"] = encryption_type
                    
                    if auth_server != None:
                        self.__generic_set_command(section_name, "auth_server", auth_server)
                        bss_entry["auth_server"] = auth_server
                    if auth_port != None:
                        self.__generic_set_command(section_name, "auth_port", auth_port)
                        bss_entry["auth_port"] = auth_port
                    if auth_secret != None:
                        self.__generic_set_command(section_name, "auth_secret", auth_secret)
                        bss_entry["auth_secret"] = auth_secret
                    if acct_server != None:
                        self.__generic_set_command(section_name, "acct_server", acct_server)
                        bss_entry["acct_server"] = acct_server
                    if acct_port != None:
                        self.__generic_set_command(section_name, "acct_port", acct_port)
                        bss_entry["acct_port"] = acct_port
                    if acct_secret != None:
                        self.__generic_set_command(section_name, "acct_secret", acct_secret)
                        bss_entry["acct_secret"] = acct_secret
                    if nasid != None:
                        self.__generic_set_command(section_name, "nasid", nasid)
                        bss_entry["nasid"] = nasid
                    
                # All encryption taken care of; moving on to basic settings
                self.__generic_set_command(section_name, "device", radio)
                self.__generic_set_command(section_name, "mode", "ap")
                bss_entry["mode"] = "ap"
                self.__generic_set_command(section_name, "ssid", ssid)
                bss_entry["ssid"] = ssid
                
                bss_list.append(bss_entry)
            
        
        # Use Heming's modified hostapd
        else:
            # Generate simple hostapd bss config file and uci CLI to load
            pass
        
    def remove_bss(self, bss):
        # Removes a bss from a radio
        pass
