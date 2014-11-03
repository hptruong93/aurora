# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import subprocess, os, inspect, tempfile
import psutil, copy
import random
import time
import WARPRadio
import inspect

import exception

def ln(stringhere):
    print "%s -------------------------------------------> %s"% (inspect.currentframe().f_back.f_lineno, stringhere)

####
# Implementation note: there are two 'databases', so to speak.
# The first is in the Database class, the second
# is UCI.  While this is redundant and inefficient,
# the only other possible implementation would be to use UCI
# as a database, which would make the Database class OpenWRT-specific.
# This is not something I wish to have - it's bad enough the radio
# is specific to OpenWRT.

class OpenWRTWifi:
    """Responsible for configuring the WiFi radio interfaces of a device.
    This version is OpenWRT specific.  For other distributions or OSes,
    create a class that implements the same functions
    as appropriate for that distro or OS."""

    WIRELESS_FILE_PATH = "/etc/config/wireless"


    def __init__(self, database):
        self.change_pending = {}
        self.database = database
        self.database.hw_list_all()
        self.radio = WARPRadio.WARPRadio()
        self.setup()        
        self.hostapd_processes = {}

    def setup(self):
        """This method removes any existing wireless configuration, subsequently
        detecting and adding any radios available to Aurora for use."""

        print("Finding and setting up radios")

        # Bring down any existing wifi
        self.radio.wifi_down()
        
        # First, remove wireless configuration file; ignore errors
        try:
            os.remove(self.WIRELESS_FILE_PATH)
        except Exception:
            pass

        # Regenerate it.  We rely on wifi detect, especially
        # since it can detect the MAC address & number of radios
        self.radio.wifi_detect()

        # wait for the reply from WARPRadio.py
        while self.radio.detect == 0:
            pass

        # Add package name to string, since UCI needs it
        detect2 = "package wireless\n" + self.radio.detect

        # Call UCI, import the data (UCI automatically commits)
        command = ["uci", "import"]
        print "\n  $ "," ".join(command)

        # uci_process = subprocess.Popen(["uci", "import"], stdin=subprocess.PIPE)
        # uci_process.communicate(input=detect2)


        # Count # radios
        # Each device has 1 wifi-device section
        num_radios = detect2.split().count("wifi-device")

        # Set # radios in database
        self.database.hw_set_num_radio(num_radios)
        self.database.hw_set_num_radio_free(num_radios)

        # For each radio, set up the database
        for count in range(0, num_radios):
            # radio_data = {"name":"radio" + str(count), "if_name":"wlan" + str(count), "bss_list":[] }
            # radio_data["channel"] = self.__radio_get_command(count, "channel")
            # radio_data["hwmode"] = self.__radio_get_command(count, "hwmode")
            # # Disabled should be stored as a number, not a string
            # radio_data["disabled"] = int(self.__radio_get_command(count, "disabled"))
            # radio_data["macaddr"] = self.__radio_get_command(count, "macaddr")
            # # This is the OpenWRT (or hostapd) limit
            # radio_data["bss_limit"] = self.database.hw_get_max_bss_per_radio()

            # change back to the above when done testing /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
            
            radio_data = {"name":"radio" + str(count), "if_name":"wlan" + str(count), "bss_list":[] }
            radio_data["channel"] = "11"
            radio_data["hwmode"] = "g"
            # Disabled should be stored as a number, not a string
            radio_data["disabled"] = 1
            if count is 0:
                radio_data["macaddr"] = "00:80:48:75:1e:47"
                # This is the OpenWRT (or hostapd) limit
                radio_data["bss_limit"] = self.database.hw_get_max_bss_per_radio()
            else:
                radio_data["macaddr"] = "00:80:48:75:1e:4c"
                # This is the OpenWRT (or hostapd) limit
                radio_data["bss_limit"] = self.database.hw_get_max_bss_per_radio()

            self.database.hw_add_radio_entry(radio_data)

            
        print self.database.hw_list_all()

        # Delete default BSS; there will be as many as the # of radios
        for count in reversed(range(0,num_radios)):
            self.radio._uci_delete_bss_index(count)

        print("Radio setup complete.  They can now be used by Aurora.")


    def setup_radio(self, name, disabled=0, channel=None, hwmode=None, txpower=None, country=None, bss_limit=None):
        """Sets up a radio with the given parameters.  If parameters
        are unspecified, existing parameters are left unchanged.
        By default, it will enable the radio interface."""

        # print "name = %s" % name
        # print "disabled = %s" % disabled
        # print "channel = %s" % channel
        # print "hwmode = %s" % hwmode
        # print "txpower = %s" % txpower
        # print "country = %s" % country


        disabled = int(disabled)
        radio_entry = self.database.hw_get_radio_entry(name)
        radio_num = name.lstrip("radio")
        current_disabled = radio_entry["disabled"]

        ln(" current disabled:%s" % current_disabled)

        # If the command is to disable and not currently disabled
        # We increment the number of free radios
        if disabled:
            if not current_disabled:
                self.database.hw_set_num_radio_free(self.database.hw_get_num_radio_free()+1)
                self.change_pending[name]['disabled'] = True

        # Opposite situation
        else:
            if current_disabled:
                self.database.hw_set_num_radio_free(self.database.hw_get_num_radio_free()-1)
                self.change_pending[name] = True

        # Write to database and UCI
        radio_entry["disabled"] = disabled

        ln( "radio_entry: %s" % str(radio_entry))

        self.radio._radio_set_command(radio_num, "disabled", disabled)

        if channel != None:
            self.radio._radio_set_command(radio_num, "channel", channel)
            radio_entry["channel"] = channel
            self.change_pending[name]['channel'] = channel

        if hwmode != None:
            self.radio._radio_set_command(radio_num, "hwmode", hwmode)
            radio_entry["hwmode"] = hwmode
            self.change_pending[name]['hwmode'] = hwmode

        if txpower != None:
            self.radio._radio_set_command(radio_num, "txpower", txpower)
            radio_entry["txpower"] = txpower
            self.change_pending[name]["txpower"] = txpower

        if country != None:
            self.radio._radio_set_command(radio_num, "country", country)
            radio_entry["country"] = country
            self.change_pending[name]["country"] = country

        if bss_limit != None:
            radio_entry["bss_limit"] = bss_limit


    def apply_changes(self):
        """Resets and applies changes on any radios that require it, such as a 
        channel change or a modification of the main BSS.
        An exception will be raised if a hostapd failure occurs and the changes
        are not applied.
        
        If there are no changes to apply, the above hostapd check will still run,
        raising an error if a hostapd instance that is supposed to run
        is not doing so."""

        # If there are no changes pending, commit will do nothing
        # Previous versions of this code used "uci commit" to
        # affect the changes. Now, a dictionary is used to store
        # pending changes and each 

        # If no radios require changes, this will not execute
        for radio in self.change_pending:
            
            # command = ["wifi", "down", str(radio)]
            # print "\n  $ "," ".join(command)
            # self.radio.wifi_down(radio)
            #subprocess.call(["wifi", "down", str(radio)])            
            
            # command = ["wifi", "up", str(radio)]
            # print "\n  $ "," ".join(command)
            # self.radio.wifi_up(radio)
            #subprocess.call(["wifi", "up", str(radio)])

            self.radio._bulk_radio_set_command(radio)
            
            radio_entry = self.database.hw_get_radio_entry(radio)
            # If a radio is disabled, do not try adding bss
            if radio_entry["disabled"] == 0:
                # Bring up any stored BSS
                for bss in radio_entry["bss_list"]:

                    if (bss["main"] == False):
                        temp_bss = copy.deepcopy(bss)
                        # add_bss does not accept a main value; we delete it                    
                        del temp_bss["main"]
                        self.add_bss(radio=radio, new_entry=False, **temp_bss)

        self.change_pending.clear()



        # Make sure hostapd still running
        # # of hostapd instance = # of radios
        num_hostapd = 0
        for process in psutil.process_iter():
            if process.name() == "hostapd":
                num_hostapd = num_hostapd + 1


        # num_radios_in_use = self.database.hw_get_num_radio() - self.database.hw_get_num_radio_free()
        # print "______---_---------_--__--___--____number radio is %s and number free is %s so number in use is %s" % (self.database.hw_get_num_radio(), self.database.hw_get_num_radio_free(), num_radios_in_use)


        if num_hostapd != num_radios_in_use:
            raise exception.hostapdError("There should be " + str(num_radios_in_use) + " hostapd instances running; there are only " + str(num_hostapd) + " instead.")

    # def __radio_set_command(self, radio_num, command, value):
    #     # We str() value, radio and command in case they are not strings (i.e. int)
    #     prtcmd = ["uci","set","wireless.radio" + str(radio_num) + "." + str(command) + "=" +str(value)]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.check_call(["uci","set","wireless.radio" + str(radio_num) + "." + str(command) + "=" +str(value)])

    def __radio_get_command(self, radio_num, command):
        # rstrip is used to remove newlines from UCI
        prtcmd = ["uci","get","wireless.radio" + str(radio_num) + "." + str(command)]
        #print "\n  $ "," ".join(prtcmd)
        #return subprocess.check_output(["uci","get","wireless.radio" + str(radio_num) + "." + str(command)]).rstrip()

    # def __generic_set_command(self, section, command, value):
    #     prtcmd = ["uci","set", "wireless." + str(section) + "." + str(command) + "=" +str(value)]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.check_call(["uci","set", "wireless." + str(section) + "." + str(command) + "=" +str(value)])

    # def __create_new_section(self, section_type, name):
    #     prtcmd = ["uci","set", "wireless." + str(name) + "=" +str(section_type)]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.check_call(["uci","set", "wireless." + str(name) + "=" +str(section_type)])

    def __generic_get_command(self, section, command):
        prtcmd = ["uci","get","wireless." + str(section) + "." + str(command)]
        #print "\n  $ "," ".join(prtcmd)
        #return subprocess.check_output(["uci","get","wireless." + str(section) + "." + str(command)]).rstrip()

    # def __uci_delete_section_name(self, section):
    #     prtcmd = ["uci","delete","wireless." + str(section)]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.call(["uci","delete","wireless." + str(section)])

    # def __uci_delete_bss_index(self, bss_num):
    #     prtcmd = ["uci","delete","wireless.@wifi-iface[" + str(bss_num) + "]"]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.call(["uci","delete","wireless.@wifi-iface[" + str(bss_num) + "]"])

    # def __uci_delete_radio(self, radio_num, section):
    #     prtcmd = ["uci","delete","wireless.radio" + str(radio_num) + "." + str(section)]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.call(["uci","delete","wireless.radio" + str(radio_num) + "." + str(section)])

    # def __uci_add_wireless_section(self, section):
    #     prtcmd = ["uci","add","wireless",str(section)]
    #     print "\n  $ "," ".join(prtcmd)
    #     subprocess.call(["uci","add","wireless",str(section)])

    def add_bss(self, radio, name, mode=None, encryption_type=None, key=None, auth_server=None, auth_port=None, auth_secret=None, acct_server=None, acct_port=None, acct_secret=None,nasid=None, new_entry=True, macaddr=None, if_name=None):
        """Creates a new BSS attached to the specified radio.  By default,
        there is no encryption.  Use the encryption_type and key values to set up.
        Passphrases must follow encryptions requirements (i.e. WPA/WEP require
        specific passphrase lengths)
        
        Possible encryption types include wep-open, wep-shared, psk (WPA-PSK) 
        and psk2 (WPA-PSK2).
        
        The encryption_type may also be set to wpa or wpa2, which will
        enable the use of WPA-Enterprise using TKIP or CCMP as ciphers,
        respectively.  Enterprise security requires some options; see
        http://wiki.openwrt.org/doc/uci/wireless for details.  Generally,
        you will need at least an auth_server and auth_secret.
        
        Mode is forced to access point for now.
        
        new_entry should be false only when non-main SSIDs are desired
        without a corresponding entry in the database. This is used
        specifically when restoring a configuration that already
        exists in the database but has not been set on the radio. The macaddr
        parameter is required with new_entry. if_name should also be specified
        in this case; otherwise, the actual configuration will not match the
        database.
        
        In general, if_name can be specified when adding a bss, and, if possible,
        it will be used.  If not specified (or the radio has no BSS, hence,
        the new BSS will be a main one) a default one will be generated/used.
        
        Exceptions will be raised for a number of common encryption
        configuration errors, but not all - in particular WPA at the
        enterprise level.  Exceptions will also (likely) be raised
        if a bss cannot be added to an active radio.
        """

        # Get associated radio and number of bss's
        radio_entry = self.database.hw_get_radio_entry(radio)
        radio_num = radio.lstrip("radio")
        bss_list = radio_entry["bss_list"]
        total_bss = len(radio_entry["bss_list"])

        # Check for existing BSS with same name but only if we are creating a new entry
        if new_entry:
            for bss in bss_list:
                if bss["name"] == name:
                    raise exception.InvalidSSID("SSID " + name + " is already in use.")

            if total_bss >= radio_entry["bss_limit"]:
                raise exception.ReachedBSSLimitOnRadio("The BSS limit of " + str(radio_entry["bss_limit"]) + " has been reached on " + radio)

        # If we have new_entry=False,
        # it is safe to assume we are not dealing with a main BSS; no verification necessary here
        main_bss = False
        # if total_bss == 0:
        #     main_bss = True

        # Create (future) database entry
        bss_entry ={}

        # Run some encryption sanity checks

        if name == None or name == '':
            raise exception.InvalidSSID()

        if encryption_type == None or encryption_type == "none":
            # Variable that determines how encryption is set
            # 0 for none, 1 for personal, 2 for enterprise
            encryption_category = 0

        elif encryption_type == "psk2" or encryption_type == "psk":
            encryption_category = 1
            if key == None:
                raise exception.InvalidKey("Key must be specified.")
            if len(key) < 8:
                raise exception.InvalidKey("Key must be at least 8 characters long")
            if len(key) > 64:
                raise exception.InvalidKey("Key cannot be more that 64 characters long.")

        elif encryption_type == "wep-shared" or encryption_type == "wep-open":
            encryption_category = 1
            if key == None:
                raise exception.InvalidKey("Key must be specified.")
            elif len(key) != 5 and len(key) != 13 and len(key) != 10 and len(key) != 26:
                    raise exception.InvalidKey("Key must be either 5/13 characters or 10/26 digits if hex.")

        elif encryption_type == "wpa" or encryption_type == "wpa2":
            encryption_category = 2
            # What enterprise allows varies wildly depending on the setup; we can't check here
            # The user will have to check himselfS
        else:
            raise exception.InvalidEncryption("Encryption type of " + encryption_type + " is not valid.")

        
        # Generate simple hostapd bss config file and use CLI to load
        # Interface name not specified -> assign, else, use given name
        if if_name == None:
            # fixed to wlan0, perious was (+ str(radio_num) + "-" + str(total_bss))
            if_name = "wlan0"
        bss_entry["if_name"] = if_name
        config_file = "interface=" + if_name + "\n"
        config_file += "driver=nl80211"  + "\n"
        # config_file += "ctrl_interface=/var/run/hostapd\n"
        # config_file += "ctrl_interface_group=0\n"
        config_file += "channel=" + radio_entry["channel"]  + "\n"
        config_file += "hw_mode=" + "g\n"#radio_entry["hwmode"] + "\n"
        config_file += "disassoc_low_ack=1\n"
        config_file += "ssid=" + name + "\n"
        config_file += "wmm_enabled=1\n"
        config_file += "ignore_broadcast_ssid=0\n"
        config_file += "preamble=1\n"
        bss_entry["encryption_type"] = "none"

        # Basic params set, now encryption
        # We do nothing if category=0
        # cat 1 = psk/wep
        if encryption_category == 1:
            if encryption_type == "psk":
                config_file += "wpa=1\n"
                config_file += "wpa_passphrase=" + key + "\n"
                config_file += "wpa_pairwise=TKIP\n"
            elif encryption_type == "psk2":
                config_file += "wpa=2\n"
                config_file += "wpa_passphrase=" + key + "\n"
                # hostapd should use wpa_pairwise, but it doesn't for some reason
                config_file += "rsn_pairwise=CCMP\n"
            elif "wep" in encryption_type:
                config_file += "wep_default_key=0\n"
                config_file += 'wep_key0="' + key + '"\n'
                config_file += "wpa=0\n"
                if encryption_type == "wep-open":
                    config_file += "auth_algs=1\n"
                elif encryption_type == "wep-shared":
                    config_file += "auth_algs=2\n"


            bss_entry["encryption_type"] = encryption_type
            bss_entry["key"] = key

        elif encryption_category == 2:

            # For all enterprise
            config_file += "disable_pmksa_caching=1\n"
            config_file += "okc=0\n"
            config_file += "eapol_key_index_workaround=1\n"
            config_file += "ieee8021x=1\n"
            config_file += "wpa_key_mgmt=WPA-EAP\n"
            config_file += "wpa=2\n"
            config_file += "wpa_pairwise=CCMP\n"

            # We only set variables if specified.
            # The requirements for enterprise are not checked, as they can
            # vary a lot and are quite complex.
            if auth_server != None:
                config_file += "auth_server_addr=" + auth_server + "\n"
                bss_entry["auth_server"] = auth_server
            if auth_port != None:
                config_file += "auth_server_port=" + auth_port + "\n"
                bss_entry["auth_port"] = auth_port
            if auth_secret != None:
                config_file += "auth_server_shared_secret=" + auth_secret + "\n"
                bss_entry["auth_secret"] = auth_secret
            if acct_server != None:
                config_file += "acct_server_addr=" + acct_server + "\n"
                bss_entry["acct_server"] = acct_server
            if acct_port != None:
                config_file += "acct_server_port=" + acct_port + "\n"
                bss_entry["acct_port"] = acct_port
            if acct_secret != None:
                config_file += "acct_server_shared_secret=" + acct_secret + "\n"
                bss_entry["acct_secret"] = acct_secret
            if nasid != None:
                config_file += "nas_identifier=" + nasid + "\n"
                bss_entry["nasid"] = nasid

            bss_entry["encryption_type"] = encryption_type

        # Encryption complete; finish up other parameters
        # and apply

        

        

        if new_entry:
            final_mac = self._generate_random_MAC_addr()

        else:
            final_mac = macaddr

        config_file += "bssid=" + final_mac  + "\n"
        config_file += "supported_rates=110 60 90 120 180 240 360 480 540"
        temp_file = open('hostapd_file', 'w')#tempfile.NamedTemporaryFile()
        temp_file.write(config_file)
        temp_file.flush()
        temp_file.close()

        # Now that it's written, we tell hostapd to read it

        print config_file

        command = ["hostapd", "-d", temp_file.name]
        # command = ["hostapd", "-ddd", '/home/kevinhan/aurora/python-auroraagent/auroraagent/hostapd_filee']
        self.hostapd_processes[radio + name] = psutil.Popen(command)

        time.sleep(1)
        if new_entry:
            # print "\n  $ "," ".join(command)
            # subprocess.call(command)
            # Write to database
            bss_entry["mode"] = "ap"
            bss_entry["name"] = name
            bss_entry["main"] = True
            bss_entry["macaddr"] = final_mac
            bss_list.append(bss_entry)
        else:
        	pass
            # print "\n  $ "," ".join(command)
            # subprocess.check_call(command)
            # Already exists in database,no need to write

        # num_hostapd = 0
        # for process in psutil.process_iter():
        #     if process.name == "hostapd":
        #         num_hostapd = num_hostapd + 1


        # num_radios_in_use = self.database.hw_get_num_radio() - self.database.hw_get_num_radio_free()
        # print "number radio is %s and number free is %s so number in use is %s" % (self.database.hw_get_num_radio(), self.database.hw_get_num_radio_free(), num_radios_in_use)
        # print "jajajajajajajjajajajajajajnumber of actual run is %s" % num_hostapd

        # if self.hostapd_processes[radio + name].poll() == None:
        #     print "-----------------__________________--------------__----------still running"
        #     print self.hostapd_processes[radio+name]


    def remove_bss(self, radio, name):
        """The bss associated to the radio is removed on the fly.  
        If the radio is currently disabled, it is removed from the database and 
        will not be reinitialized when the radio is enabled again.
        
        If a main BSS is removed, all BSS on that radio will be removed
        and the radio will be disabled.
        
        An exception will be raised if a non-existent SSID is given."""

        # Get relevant data
        radio_entry = self.database.hw_get_radio_entry(radio)
        radio_num = radio.lstrip("radio")
        bss_list = radio_entry["bss_list"]

        bss_entry = None
        # Get actual entry based on SSID
        for bss in bss_list:
            if bss["name"] == name:
                bss_entry = bss

        if bss_entry is None:
            # Nothing to do, likely already deleted
            return

        # If we have a "main" BSS, we must use UCI
        elif bss_entry["main"]:
            # We set the format of the name in add_bss, now we simply delete the section
            self.radio._uci_delete_section_name("BSS" + radio_num)
            self.hostapd_processes[radio + name].terminate()
            self.hostapd_processes[radio + name].wait()

            del self.hostapd_processes[radio+name]
            # Remove database entries of all BSS for the radio
            # Otherwise, we get problems if other users depend on use and we delete and try to recreate a slice
            del bss_list[0:len(bss_list)]
            # TODO: Sync this up with the slice data.  As it stands, someone with an SSID on a radio owned
            # by someone else will still have their slice marked "active" when it was in fact deleted by the radio owner

        # else:
        #     # It is possible that the radio may be marked as disabled
        #     # but waiting for changes to be applied, or vice versa.
        #     # Regardless, this code will eliminate the BSS, even if 
        #     # the remove command fails because the interface is down.
        #     command = ["hostapd_cli", "-p", "/var/run/hostapd-phy" + str(radio_num), "del_bss", name]
        #     print "\n  $ "," ".join(command)
        #     subprocess.call(["hostapd_cli", "-p", "/var/run/hostapd-phy" + str(radio_num), "del_bss", name])
        #     bss_list.remove(bss_entry)

    def modify_bss(self, radio, name, new_name=None, encryption_type=None, key=None):
        pass

    def _generate_random_MAC_addr(self):
        """Generates a random and appropriate `MAC address \
        <http://en.wikipedia.org/wiki/MAC_address>`_.

        A MAC address is 48 bytes long and has the format
        ``11:22:33:44:55:66``.  
        
        The most significant byte (in this case 0x11) contains 
        information about the station broadcasting the MAC 
        address::
        
            0x02 = 0000 0010
                          ^^
                          |+- Multicast bit: always set this to 0, 
                          |     as we are only ever doing unicast
                          +-- Global or local MAC addr: 
                                because we are generating the MAC addr
                                ourselves, always set this to 1: local

        :returns: str -- Random and valid MAC address
        
        """
        mac = [0x02]
        for i in range(5):
            mac.append(random.randint(0x00, 0xff))
        mac_str = ':'.join(map(lambda x: "%02x" % x, mac))
        return mac_str
