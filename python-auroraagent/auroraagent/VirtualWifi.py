# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, os, pprint
import exception

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

        try:
            configuration[0]["attributes"]["channel"] = int(configuration[0]["attributes"]["channel"])
        except:
            pass

        try:
            configuration[0]["attributes"]["txpower"] = int(configuration[0]["attributes"]["txpower"])
        except:
            pass

        try:
            configuration[0]["attributes"]["bss_limit"] = int(configuration[0]["attributes"]["bss_limit"])
        except:
            pass
        

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

        # Order of BSS/radio disabling is important now that we are deleting a slice on the WARP board and
        # its associated hostapd process. If the slice cannot be deleted, we need the database information on that slice
        # to remain the same as it was before we tried to delete it.
        
        wifi_radio = [interace in configuration if interace['flavor'] == 'wifi_radio'][0]
        wifi_bss = [interace in configuration if interace['flavor'] == 'wifi_bss'][0]

        self.wifi.remove_bss(wifi_bss["attributes"]["radio"],wifi_bss["attributes"]["name"])
        self.database.delete_entry("RadioInterfaces", wifi_bss["attributes"]["name"])
        self.wifi.setup_radio(wifi_radio["attributes"]["name"], disabled=1)
            


            # for interface in configuration:
            #     
            #     try:
            #         if interface["flavor"] == "wifi_radio" and flavor_changes_complete["wifi_bss"]:
            #             # only make changes if we have already attempted to delete bss and successfully deleted the slice
            #             if deleted_on_WARP:
            #                 self.wifi.setup_radio(interface["attributes"]["name"], disabled=1)  
            #             # even if we didn't make any changes due to not being able to delete the slice, we say that the action is complete since
            #             # there's nothing else that we can do with this configuration. In the future, we should reattempt slice deletion given certain return
            #             # conditions from WARP. 
            #             flavor_changes_complete["wifi_radio"] = True
            #         elif interface["flavor"] == "wifi_bss" and not flavor_changes_complete["wifi_bss"]:
            #             # this conditional is for the following problem situation: if we see the wifi_radio flavor first then we will have to skip 
            #             # it and move on to wifi_bss. Because of this we will need to cycle through the configuration flavors a second time and may
            #             # see wifi_bss first this time. As such, we will skip it since the proper action has already been performed on this flavor
            #             try:
            #                 self.wifi.remove_bss(interface["attributes"]["radio"],interface["attributes"]["name"])
            #             except:

            #             if deleted_on_WARP:
            #                 self.database.delete_entry("RadioInterfaces", interface["attributes"]["name"])
            #     except:
            #         pass
    
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

        
       
