# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, os

class VirtualWifi:
    """Responsible for configuring the WiFi radio interfaces of a device.
    Abstracts away implementation specific code."""
    
    ###
    # Note re database: OpenWRTWifi (or other implementation)
    # fills in/updates/uses the HARDWARE database, being low-level.
    # It does not care about slices. Instead, this class
    # - Virtual Wifi - is responsible for updating the higher level
    # database, in the same league as VirtualBridges or VirtualInterfaces.
    
    MODULE_JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),'modules.json')
    MODULES_FOLDER = 'modules'


    def __init__(self, database):

        # Load database
        self.database = database
        
        # Load correct implementation of Wifi, depending
        # on current OS
        json_file = open(self.MODULE_JSON_FILE)
        self.wifi = self.__load_module(self.database.hw_get_firmware_name(), json.load(json_file)["VirtualWifi"])
        json_file.close()
        
        
    def __load_module(self, flavor, metadata):
        
        # Cast to string - some issues with unicode?  Also, append Wifi to name
        flavor = str(flavor) + "Wifi"
        
        module_file = __import__(self.MODULES_FOLDER,globals(),locals(),
                [flavor]).__dict__[flavor]
        module_class_name = metadata[flavor]['class']
        
        module_class = getattr(module_file, module_class_name)
        module_instance = module_class(self.database)
        
        return module_instance
        
            
            
    def create_slice(self, configuration):
        """Sets up radios and adds any BSS specified.
        Will restart radios only if required."""
        
        # Set up radios only first
        for interface in configuration:
            if interface["flavor"] == "wifi_radio":
            
                self.database.add_entry("RadioInterfaces", "wifi_radio", interface["attributes"])
                
                self.wifi.setup_radio(**interface["attributes"])
                
                
        # Now setup BSS
        for interface in configuration:
            if interface["flavor"] == "wifi_bss":

                self.database.add_entry("RadioInterfaces", "wifi_bss", interface["attributes"])
                
                self.wifi.add_bss(**interface["attributes"])
                
         
        self.wifi.apply_changes()
        
    
    def delete_slice(self, configuration):
        """Deletes any BSS and/or radios in the slice.
        Note that the radio will be reset only if required.
        Data other than names of radios or SSIDs is not parsed or stored."""
        
        
        for interface in configuration:
            # Order of BSS/radio disabling is not important
            try:
                print "----------------- flavor:" + interface['flavor']
                if interface["flavor"] == "wifi_radio":
                    self.wifi.setup_radio(interface["attributes"]["name"], disabled=1)
            
                elif interface["flavor"] == "wifi_bss":
                    self.wifi.remove_bss(interface["attributes"]["radio"],interface["attributes"]["name"])

                self.database.delete_entry("RadioInterfaces", interface["attributes"]["name"])
            except:
                pass

                
        self.wifi.apply_changes()
    
    def modify_slice(self, configuration):
        """Modifies BSS parameters specified, without restarting any 
        radios. Modification of radios requires the use of 
        delete/create. 

        TODO(mike): Determine whether it is possible to change network 
        SSID without restarting a radio.  If not, slice modification of 
        SSID will require extra special care - modifying the main bss 
        would be a special case and require a different procedure than
        for an auxiliary slice.

        :param dict configuration:

        """
        # raise Exception("Modify for WiFi not implemented.")
        for interface in configuration:
            # Only BSS parameters are allowed
            if interface["flavor"] == "wifi_bss":
                # TODO(mike)
                #self.wifi.
                pass
            # self.database.replace_entry("RadioInterfaces", )

    # TODO(mike)!!!
    # def restart_slice(self

        
       
