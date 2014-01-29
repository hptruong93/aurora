# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import VirtualBridges, VirtualInterfaces
import exception, json, pprint, Database, atexit, sys
import VirtualWifi
import Monitor
import subprocess

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
        self.monitor = Monitor.Monitor(self.database)

        # Clean up on exit
        atexit.register(self.__reset)

    def __find_main_slice(config):
        for slice, attributes in config["init_database"].iteritems():
            for item in attributes["RadioInterfaces"]:
                if item["flavor"] == "wifi_radio":
                    return slice
        return None

    def __setup_existing_slices(self, config):
        main_slice = __find_main_slice(config)
        if not main_slice:
            # No slices configured
            self.database = Database.Database(config)
        else:
            pass
            #Set up slices
            #self.create_slice(main_slice   UNFINISHED
    
    def create_slice(self, slice, user, config):
        """Create a slice with the given confiuration.
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
            except Exception as e:
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
                            print " [v] Exception: %s" %e.message
                            # Abort, delete
                            self.delete_slice(slice)
                            raise exception.SliceCreationFailed("Aborting.\nError applying setting " + setting + " to port " + port + " on bridge " + bridge_name + '\n' + e.message)


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
            # Delete all virtual interfaces
            for interface in slice_data['VirtualInterfaces']:
                try:
                    self.v_interfaces.delete(interface['attributes']['name'])
                except:
                    print("Error: Unable to delete virtual interface " + interface['attributes']['name'])

            # Delete wifi
            try:
                self.wifi.delete_slice(slice_data["RadioInterfaces"])
            except:
                # With WiFi, sometimes hostapd can take a while to be brought down
                # and the WiFi code thinks something screwy happened since
                # hostapd is still running when it should have been killed.
                # Everything is OK, though, since it gets killed a few msecs later.
                print("Error: Exception encountered deleting wifi for " + slice + ". Likely not a cause for concern.")


        # Delete database entry; catch errors
        try:
            print ">>>"
            self.database.delete_slice(slice)
            print "<<<"
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

        At this time, this restricts the commands to port and
        bridge modifications from the VirtualBridge module,
        with no support for port addition or deletion."""

        self.database.set_active_slice(slice)

        data = config["VirtualBridges"]
        name = data["name"]
        # Bridge settings
        for setting in data["bridge_settings"]:
            self.v_bridges.modify_bridge(name, setting, data["bridge_settings"][setting])
        # Port settings
        for port in data["port_settings"]:
            for port_setting in data["port_settings"][port]:
                self.v_bridges.modify_port(name, port, port_setting, data["port_settings"][port][port_setting])

        self.database.reset_active_slice()

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
        elif command == "remote_API":
            # The remote API can return data
            return self.remote_API(slice, config)
        elif command == "restart":
            return self.restart()
        elif command == "reset":
            return self.__reset()
        elif command == "update":
            return self.monitor.get_status()
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
