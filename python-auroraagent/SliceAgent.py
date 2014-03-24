# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import VirtualBridges, VirtualInterfaces, VirtualTC
import exception, json, pprint, Database, atexit, sys
import VirtualWifi
import Monitor
import subprocess
import time
import traceback
import types

class SliceAgent:
    """The Slice Agent is the high level interface to the creation,
    modification and deletion of slices."""

    # Network class will receive packet -> decode ->
    # send command and config to the execute() method in this file

    def __init__(self, config):
        # config is a dictionary containing
        # base configuration information. It should be passed to classes
        # that need the data; they can each take what they need
        # and ignore what they don't.

        self.database = Database.Database(config)
        # Init sub classes
        self.v_bridges = VirtualBridges.VirtualBridges(self.database)
        self.v_interfaces = VirtualInterfaces.VirtualInterfaces(self.database)
        self.wifi = VirtualWifi.VirtualWifi(self.database)
        self.tc = VirtualTC.VirtualTC(self.database)
        self.monitor = Monitor.Monitor(self.database)

        # Clean up on exit
        atexit.register(self.__reset)

    def create_slice(self, slice, user, config):
        """Create a slice with the given configuration.
        Will raise exceptions if errors are encountered."""

        # Make sure slice does not already exist
        if slice in self.database.get_slice_list():
            raise exception.SliceCreationFailed("Slice " + slice  + " already exists!")


        print "Creating slice", slice

        # Create datbase entry
        self.database.create_slice(slice, user)
        self.database.set_active_slice(slice)

        # Parse config

        # Create wifi slices
        try:
            self.wifi.create_slice(config["RadioInterfaces"])
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            print " [v] Exception: %s" %e.message
            self.delete_slice(slice)
            # DEBUG
            #raise
            raise exception.SliceCreationFailed("Aborting. Unable to create WiFi slice for " + str(slice) + '\n'
                                                + e.message)

        # Create all virtual interfaces
        for interfaces in config['VirtualInterfaces']:
            try:
                self.v_interfaces.create(interfaces["flavor"], interfaces["attributes"])
                #Hard code check for eth0 - this is uplink interface
                if_names = (interfaces["attributes"]["attach_to"], interfaces["attributes"]["name"])
                if if_names[0] == "eth0":
                    vif_up = if_names[1]
                else:
                    vif_down = if_names[1]
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                print " [v] Exception: %s" %e.message
                # Abort, delete
                self.delete_slice(slice)
                raise exception.SliceCreationFailed("Aborting.\nVirtual Interface creation failed: " + interfaces['attributes']['name'] + '\n' + e.message)


        # Create all virtual bridges
        for bridges in config['VirtualBridges']:
            bridge_name = bridges['attributes']['name']
            try:
                self.v_bridges.create_bridge(bridges['flavor'], bridge_name)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                # Abort, delete
                print " [v] Exception: %s" %e.message
                self.delete_slice(slice)
                raise exception.SliceCreationFailed("Aborting.\nBridge creation failed: " + bridge_name + '\n' + e.message)
            else:
                # Bridge created, now apply the settings
                # Add ports
                for port in bridges['attributes']['interfaces']:
                    try:
                        self.v_bridges.add_port_to_bridge(bridge_name, port)
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        print " [v] Exception: %s" %e.message
                        # Abort, delete.
                        self.delete_slice(slice)
                        raise exception.SliceCreationFailed("Aborting.\nError adding port " + port + " to bridge " + bridge_name + '\n' + e.message)

                # Bridge settings
                setting_list = bridges['attributes']['bridge_settings']
                for setting in setting_list:
                    try:
                        self.v_bridges.modify_bridge(bridge_name, setting, setting_list[setting])
                    except Exception as e:
                        traceback.print_exc(file=sys.stdout)
                        print " [v] Exception: %s" %e.message
                        # Abort, delete. Settings don't matter when deleting
                        self.delete_slice(slice)
                        raise exception.SliceCreationFailed("Aborting.\nError applying setting " + setting + " to bridge " + bridge_name + '\n' + e.message)

                # Port settings
                for port in bridges['attributes']['port_settings']:
                    for setting in bridges['attributes']['port_settings'][port]:
                        try:
                            self.v_bridges.modify_port(bridge_name, port, setting, bridges['attributes']['port_settings'][port][setting])
                        except Exception as e:
                            traceback.print_exc(file=sys.stdout)
                            print " [v] Exception: %s" %e.message
                            # Abort, delete
                            self.delete_slice(slice)
                            raise exception.SliceCreationFailed("Aborting.\nError applying setting " + setting + " to port " + port + " on bridge " + bridge_name + '\n' + e.message)

        for traffic_control in config.get('TrafficAttributes',[]):
            try:
                #find up if
                print "vif_up,vif_down",vif_up, vif_down
                traffic_control["attributes"]["if_up"] = vif_up
                traffic_control["attributes"]["if_down"] = vif_down
                if traffic_control["flavor"] == "ovs-tc":
                    if "ovs" in self.v_bridges.module_list.keys():
                        traffic_control["attributes"]["ovs_db_sock"] = self.v_bridges.module_list["ovs"].socket_file.name
                    else:
                        raise Exception("No ovs module previously loaded")
                self.tc.create(traffic_control["flavor"], traffic_control["attributes"])
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                print " [v] Exception: %s" %e.message
                # Abort, delete
                self.delete_slice(slice)
                raise exception.SliceCreationFailed("Aborting.\nQoS creation failed\n" + e.message)
        
        self.database.reset_active_slice()

    def delete_slice(self, slice):
        """Delete a given slice, and ignore any errors that occur in
        the process in case a slice is corrupted."""
        print "Deleting slice", slice
        try:
            slice_data = self.database.get_slice_data(slice)
            self.database.set_active_slice(slice)
        except KeyError:
            # If slice does not exist, ignore
            print "...does not exist"
            #pass
        else:
            # Delete all bridges
            for bridge in slice_data['VirtualBridges']:
                try:
                    self.v_bridges.delete_bridge(bridge['attributes']['name'])
                except:
                    print("Error: Unable to delete bridge " + bridge['attributes']['name'])
            if "TrafficAttributes" in slice_data.keys():
                for traffic_control in slice_data['TrafficAttributes']:
                    try:
                        self.tc.delete(traffic_control['attributes']['name'])
                    except:
                        print("Error: Unable to remove Qos " + traffic_control['attributes']['name'])
            # Delete all virtual interfaces
            for interface in slice_data['VirtualInterfaces']:
                try:
                    self.v_interfaces.delete(interface['attributes']['name'])
                except:
                    print("Error: Unable to delete virtual interface " + interface['attributes']['name'])
            # Delete wifi
            try:
                self.wifi.delete_slice(slice_data["RadioInterfaces"])
            except exception.hostapdError as e:
                # With WiFi, sometimes hostapd can take a while to be brought down
                # and the WiFi code thinks something screwy happened since
                # hostapd is still running when it should have been killed.
                # Everything is OK, though, since it gets killed a few msecs later.
                #print "Error: Exception encountered deleting wifi for ", + slice + ". Likely not a cause for concern.")
                pass
            except Exception as e:
                traceback.print_exc(file=sys.stdout)

        # Delete database entry; catch errors
        try:
            self.database.delete_slice(slice)
        except:
            pass
        self.database.reset_active_slice()

    def modify_slice(self, slice, config):
        """The modify slice command will execute modify
        functions on various modules.  It will only execute commands
        that are not destructive or represent a significant
        topology change.  Commands not allowed
        include, but are not limited to, creating/deleting
        virtual interfaces, virtual bridges, or
        adding/deleting ports from bridges.

        Commands that deal with changing wifi settings have to be 
        used carefully.  Changing a slice SSID is easy - as long as
        the slice is not the main_bss.  If it is, uci must be used
        to reconfigure it, meaning all slices will be destructed and
        recreated.

        In case something goes wrong, backups of each slice are taken
        and are stored in self.database.prev_database - this way
        they can be recreated from their last known good configuration.

        """
        # Take a backup in case everything goes wrong
        self.database.backup_current_config()

        self.database.set_active_slice(slice)

        slice_configuration = self.database.get_slice_data(slice)

        # For DEBUGGING
        print "Previous slice configuration"
        print json.dumps(slice_configuration, indent=4)

        # Modify slice configuration to include changed attributes
        for section, new_configuration_list in config.iteritems():
            # Section contains an item among:
            #    "RadioInterfaces", "VirtualInterfaces",
            #    "VirtualBridges", "TrafficAttributes"
            for new_configuration in new_configuration_list:
                for item in slice_configuration.get(section):
                    # Use default constants of 0 and 1 force a false
                    # conditional evaluation if neither element for "name"
                    # can be found
                    if (item.get("attributes",{}).get("name", 0) == 
                            new_configuration.get(
                                "attributes",{}
                            ).get("name", 1)):
                        # We now have the item to modify: update attributes
                        for attribute_name, attribute in \
                                new_configuration.get("attributes").iteritems():
                            it = item["attributes"].get(attribute_name)
                            if type(it) is types.DictType:
                                # Item to update is a dictionary, use dict's
                                # update() method, which will only overwrite
                                # entries existing in both dicts.
                                it.update(attribute)
                            elif attribute_name == "name":
                                # Since section lookup and matching is done 
                                # by name, changing a name requires a new
                                # item in the modification config - "new_name"
                                new_name = new_configuration.get(
                                    "attributes", {}).get(
                                    "new_name"
                                )
                                if new_name is not None:
                                    item["attributes"]["name"] = new_name
                            else:
                                it = attribute

        # FOR DEBUGGING
        print "Modified slice configuration"
        print json.dumps(slice_configuration, indent=4)

        try:
            if "RadioInterfaces" in config.keys():
                self.wifi.modify_slice(config["RadioInterfaces"])
        except Exception as e:
            # Restart slices using last known good configuration
            print " [v] Exception: %s" % e.message
            self.restart_slice(slice)

            # DEBUG
            #raise
            raise exception.SliceModificationFailed(
                "Aborting. Unable to modify WiFi slice for %s\n%s" %
                (str(slice), e.message)
            )

        # --OLD--
        # try:
        #     if "VirtualBridges" in config.keys():

        # data = config["VirtualBridges"]
        # name = data["name"]
        # # Bridge settings
        # for setting in data["bridge_settings"]:
        #     self.v_bridges.modify_bridge(name, setting, data["bridge_settings"][setting])
        # # Port settings
        # for port in data["port_settings"]:
        #     for port_setting in data["port_settings"][port]:
        #         self.v_bridges.modify_port(
        #             name, port, port_setting, 
        #             data["port_settings"][port][port_setting]
        #         )

        self.database.reset_active_slice()
    
    def restart_slice(self, slice):
        """Restarts a slice by deleting it and recreating it using 
        last known good configuration from prev_database.  This 
        method should only be called from within self.modify_slice.

        The implementation of this method will have to change once 
        OpenWRTWifi is no longer the sole module responsible for 
        creation and deletion of wireless slices.  This is due to 
        the limitation of a single radio configuration per radio - if
        the main bss is deleted, all other bss on the same radio 
        will have to be restarted as well.

        """
        userid = self.database.get_slice_user(slice)
        slice_radio = self.database.get_slice_radio(slice)
        slice_config = {}
        # Populate slice_config for slices on radio in question
        slices_on_radio = self.database.hw_get_slice_id_on_radio(slice_radio)
        print slices_on_radio
        for slice_id in slices_on_radio:
            # print slice_id
            # print slice_config
            # print self.database.get_slice_data(slice_id)
            slice_config[slice_id] = self.database.get_slice_data(slice_id)


        main_bss = self.database.find_main_slice(slice_config, slice_radio)


        print ("Restarting %s... " % slice),
        if slice == main_bss:
            print ("main bss!")
            # All slices on the radio must be deleted, then the slice
            # with the main bss must be restarted first, followed by 
            # the rest.
            for slice_to_delete in slices_on_radio:
                if slice_to_delete != slice:
                    self.delete_slice(slice_to_delete)
            # All slices except that with main_bss are now deleted,
            # can delete main slice
            self.delete_slice(slice)
            # Now all slices can once again be recreated, beginning with
            # the main_bss slice
            print "Recreating %s" % slice
            self.recreate_slice(slice, userid)
            slices_on_radio.remove(slice)
            for slice_to_recreate in slices_on_radio:
                # Recreate additional slices.
                print "Recreating %s" % slice_to_recreate
                self.recreate_slice(slice_to_recreate)
        else:
            # Not a main_bss, simply delete the slice, and recreate it
            # from the previously stored database.
            self.delete_slice(slice)
            self.recreate_slice(slice, userid)
        self.database.reset_active_slice()

    def recreate_slice(self, slice, user=None):
        if (slice in self.database.prev_database.keys() and 
                slice != "default_slice"):
            if user is None:
                user = self.database.get_slice_user(slice, prev=True)
            self.create_slice(slice, user, self.database.prev_database[slice])
        else:
            raise Exception("Error: No slice configuration found for " + slice)

    def remote_API(self, slice, info):
        """The remote API command accepts a specially formatted JSON
        file containing a number of fields:
        1. module : either VirtualBridges, VirtualInterfaces or Database
        2. command : the command to execute
        3. args : a dictionary containing named arguments
        appropriate to the command (may be optional)
        For example, to execute the command get_status(tap1) in VirtualInterfaces,
        you would format info like so:
        { "module" : "VirtualInterfaces", "command" : "get_status", "args" : { "name" : "tap1"} }"""



        self.database.set_active_slice(slice)
        if info["module"] == "VirtualInterfaces":
            command = getattr(self.v_interfaces, info["command"])
        elif info["module"] == "VirtualBridges":
            command = getattr(self.v_bridges, info["command"])
        elif info["module"] == "Database":
            command = getattr(self.database, info["command"])

        self.database.reset_active_slice()
        # This won't cause any 'undefined variable' issues
        # since the JSON is verified to satisfy one of
        # the three above if statements earlier
        return command(**info["args"])

    def execute(self, slice, command, config=None, user="default_user"):
        """The main entry point for any command coming from a remote
        server.  The command is analyzed and forwaded to the relevant
        class/method as appropriate."""
        
        # determine if create, delete or modify
        if command == "create_slice":
            self.create_slice(slice, user, config)
        elif command == "delete_slice":
            self.delete_slice(slice)
        elif command == "modify_slice":
            self.modify_slice(slice, config)
        elif command == "recreate_slice":
            self.recreate_slice(slice, user)
        elif command == "remote_API":
            # The remote API can return data
            return self.remote_API(slice, config)
        elif command == "restart":
            return self.restart()
        elif command == "reset":
            return self.__reset()
        elif command == "get_stats":
            return self.monitor.get_stats()
        else:
            raise exception.CommandNotFound(command)

    def restart(self):
        # Restart machine (OS), but give time for aurora to send OK to manager
        subprocess.Popen(['sleep 5; reboot'], shell=True)
        return "RESTARTING"

    def __reset(self):
        # Clear out all slices
        for slice in self.database.get_slice_list():
            self.delete_slice(slice)

        print "Slices deleted, resetting..."
        # Execute any specific reset functions
        # Usually, these need to be executed AFTER we
        # finish using the class to delete stuff
        self.v_bridges.reset()
        self.v_interfaces.reset()
        return "AP reset"

def main():
    raise Exception("main() not implemented")

if __name__ == "__main__":
    main()