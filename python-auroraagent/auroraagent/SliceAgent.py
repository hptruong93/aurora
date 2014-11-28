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

    def shutdown(self):
        # we've received a shutdown message from Receive.py, thus we need to close down the running threads
        # in lower modules. As it stands, this only applies to the subscriber thread running in WARPRadio.py
        # so we only need to notify virtualwifi

        self.wifi.shutdown()

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
            raise exception.SliceCreationFailed("Aborting. Unable to create WiFi slice for %s \n %s" % (str(slice), e.message))

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
                if traffic_control["flavor"] == "ovs_tc":
                    if "ovs" in self.v_bridges.module_list.keys():
                        traffic_control["attributes"]["ovs_db_sock"] = self.v_bridges.module_list["ovs"].socket_file.name
                    else:
                        raise Exception("No ovs module previously loaded")
                self.tc.create(traffic_control["flavor"], traffic_control["attributes"])
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                print " [v] Exception: %s" % e.message
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
            # Delete QOS parameters
            if "TrafficAttributes" in slice_data.keys():
                for traffic_control in slice_data['TrafficAttributes']:
                    try:
                        self.tc.delete(traffic_control['attributes']['name'])
                    except Exception:
                        traceback.print_exc(file=sys.stdout)
                        print("Error: Unable to remove Qos " + traffic_control['attributes']['name'])
            # Delete all bridges
            for bridge in slice_data['VirtualBridges']:
                try:
                    self.v_bridges.delete_bridge(bridge['attributes']['name'])
                except:
                    print("Error: Unable to delete bridge " + bridge['attributes']['name'])

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

        Commands that deal with changing wifi settings are tricky to 
        implement without having to restart the radios.  Since 
        modifying the main bss and auxilary bss is a different 
        procedure, it is easier at this point to recreate the slice 
        with the modified configuration.  A more elegant solution could 
        be sought, but once protocol-based virtualization is implemented 
        this limitation will be much easier to address.  Changing a 
        slice SSID is easy - as long as the slice is not the main_bss.  
        If it is, uci must be used to reconfigure it, meaning all 
        slices will be destructed and recreated.

        SSID modification of slice with current SSID "MAIN" would
        look like::

            {
                "RadioInterfaces": [
                    {
                        "flavor" : "wifi_bss",
                        "attributes" : 
                            {
                                "name" : "MAIN",
                                "new_name": "MAIN MOD"
                            }
                    },
                ]
            }


        For modifications to bridges and interfaces, slices should not 
        have to be restarted.

        Modifying a virtual interface, such as changing the tunnel 
        endpoint for a capsulator link, requires deleting the interface
        and creating a new instance of it.  In order to delete the
        interface, the bridges associated with it must be deleted and
        reconstructed, or at least have the port disassociated with them
        so it can be removed and recreated.

        Modifying a virtual bridge is the next step, as all interfaces
        will now have been recreated.

        Modifying QOS values will be the last step, and will happen only
        once all bridges and interfaces are successfully modified.

        In case something goes wrong, backups of each slice are taken
        and are stored in self.database.prev_database - this way
        they can be recreated from their last known good configuration.

        """
        # Take a backup in case everything goes wrong
        self.database.backup_current_config()

        self.database.set_active_slice(slice)

        slice_configuration = self.database.get_slice_data(slice)
        slice_configuration_backup = slice_configuration

        # For DEBUGGING
        print "Modification configuration"
        print json.dumps(config, indent=4)
        print "Previous slice configuration"
        print json.dumps(slice_configuration, indent=4)

        # slice_configuration contains the previous configuration for
        # the slice.  the config parameter has an abbreviated dictionary
        # containing the changes to be made to slice_configuration.

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
                    if (item.get("attributes", {}).get("name", 0) == 
                            new_configuration.get(
                                "attributes", {}
                            ).get("name", 1)):
                        # We now have the item to modify: update attributes
                        for attribute_name, attribute in \
                                new_configuration.get("attributes").iteritems():
                            it = item["attributes"].get(attribute_name)
                            if it is None:
                                continue
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
                                print "Updating %s: %s to %s" % (
                                       attribute_name, it, attribute
                                )
                                item["attributes"][attribute_name] = attribute


        # FOR DEBUGGING
        print "Modified slice configuration"
        print json.dumps(slice_configuration, indent=4)

        print "Current DB:"
        print json.dumps(self.database.database, indent=4)

        if "RadioInterfaces" in config.keys():
            try:
                self.restart_slice(slice, config=slice_configuration)
            except Exception as e:
                # Restart slice using last known good configuration
                # from our prior backup
                print "Slice modifications were invalid, try"
                print "to restart from backup..."
                try:
                    self.restart_slice(slice)
                except Exception as e:
                    # Something bad happened
                    print "Could not restart slice from backup"
                    traceback.print_exc(file=sys.stdout)
                    raise exception.SliceModificationFailed(
                        "Aborting. Unable to modify WiFi slice for %s\n%s" %
                        (str(slice), e.message)
                    )
        else:
            # We know no wifi parameters are being modified, slice
            # does not have to be restarted.  Check for bridge or port
            # settings.
            if "VirtualInterfaces" in config.keys():
                for interface_conf in config["VirtualInterfaces"]:
                    port = interface_conf["attributes"]["name"]
                    # Find full configuration
                    full_interface_conf = None
                    for conf in \
                            slice_configuration["VirtualInterfaces"]:
                        if conf["attributes"]["name"] == port:
                            full_interface_conf = conf
                            break

                    associated_bridges = []
                    # Remove port from bridges to which it is attached
                    for bridge in slice_configuration['VirtualBridges']:
                        if port not in bridge["attributes"]["interfaces"]:
                            continue
                        bridge_name = bridge['attributes']['name']
                        try:
                            self.v_bridges.delete_port_from_bridge(
                                bridge_name,
                                port
                            )
                            associated_bridges.append(bridge_name)
                        except Exception:
                            traceback.print_exc(file=sys.stdout)
                            print("Error: Unable to remove port from bridge %s"
                                % bridge_name)
                            #self.restart_slice(slice)

                    # Modify the interface
                    if full_interface_conf is not None:
                        try:
                            self.v_interfaces.modify(
                                port, 
                                full_interface_conf["attributes"]
                            )
                        except Exception:
                            traceback.print_exc(file=sys.stdout)
                            print("Error: Unable to modify port %s"
                                % port)
                            #self.restart_slice(slice)

                    # Add port to all previously found associated bridges
                    for bridge_name in associated_bridges:
                        try:
                            self.v_bridges.add_port_to_bridge(
                                bridge_name,
                                port
                            )
                        except Exception:
                            traceback.print_exc(file=sys.stdout)
                            print("Error: Unable to add port to bridge %s"
                                % bridge_name)
                            #self.restart_slice(slice)

            if "VirtualBridges" in config.keys():
                for bridge_conf in config["VirtualBridges"]:
                    bridge = bridge_conf["attributes"]["name"]
                    # Find full configuration
                    full_bridge_conf = None
                    for conf in \
                            slice_configuration["VirtualBridges"]:
                        if conf["attributes"]["name"] == bridge:
                            full_bridge_conf = conf
                            break

                    if full_bridge_conf is not None:
                        for command, parameter in \
                                full_bridge_conf["attributes"]["bridge_settings"].iteritems():
                            try:
                                self.v_bridges.modify_bridge(
                                    bridge, 
                                    command, 
                                    parameter
                                )
                            except Exception:
                                traceback.print_exc(file=sys.stdout)
                                print("Error: Unable to modify bridge %s"
                                    % bridge)

            if "TrafficAttributes" in config.keys():
                print "Modification of traffic attributes is not implemented"
                raise NotImplementedError()



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
    
    def restart_slice(self, slice, user=None, config=None):
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
        if config is not None:
            # This method is being called from execute(), no database
            # backup was previously taken
            self.database.backup_current_config()
            # Find the radio the slice will be restarted on
            slice_radio = None
            for r_conf in config.get("RadioInterfaces", []):
                if r_conf.get("flavor") == "wifi_bss":
                    slice_radio = r_conf.get("attributes", {}).get(
                        "radio"
                    )
                    break

        userid = (user if (user != "default_user" and user is not None) else 
                    self.database.get_slice_user(slice))
        slice_radio = slice_radio or self.database.get_slice_radio(slice)
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


        print ("Restarting %s... " % slice)
        if slice == main_bss:
            print (" -- main bss!")
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
            try:
                self.recreate_slice(slice, userid, config)
            except Exception as e:
                print "Error recreating slice, using last known config"
                traceback.print_exc(file=sys.stdout)
                try:
                    self.recreate_slice(slice)
                except Exception as e:
                    print "------------"
                    print "Something bad happened, no known configuration"
                    print "with which to recreate slice."
                    print "Let manager know some slices are going to be"
                    print "affected."
                    print "------------"
                    traceback.print_exc(file=sys.stdout)
                    raise exception.SliceRecreationFailed()


            slices_on_radio.remove(slice)
            for slice_to_recreate in slices_on_radio:
                # Recreate additional slices.
                print "Recreating %s" % slice_to_recreate
                self.recreate_slice(slice_to_recreate)
        else:
            # Not a main_bss, simply delete the slice, and recreate it
            # from the previously stored database.
            self.delete_slice(slice)
            self.recreate_slice(slice, userid, config)
        self.database.reset_active_slice()

    def recreate_slice(self, slice, user=None, config=None):
        if user is not None and config is not None:
            self.create_slice(slice, user, config)
        else:
            if (slice in self.database.prev_database.keys() and 
                    slice != "default_slice"):
                if user is None:
                    user = self.database.get_slice_user(slice, prev=True)
                self.create_slice(slice, user, 
                                  self.database.prev_database[slice])
            else:
                raise Exception("Error: No slice configuration found for %s",
                                slice)

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
        elif command == "restart_slice":
            self.restart_slice(slice, user, config)
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
        elif command == "sync_config":
            return
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