# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import VirtualBridges, VirtualInterfaces
import exception, json, pprint, Database, atexit, sys
import OpenWRTWifi
import subprocess
    
class SliceAgent:
    """The Slice Agent is the high level interface to the creation,
    modification and deletion of slices."""
    
    # Network class will receive packet -> decode ->
    # send command and config to this class
    
    def __init__(self):
        self.database = Database.Database()
        # Init sub classes
        self.v_bridges = VirtualBridges.VirtualBridges(self.database)
        self.v_interfaces = VirtualInterfaces.VirtualInterfaces(self.database)
        self.wifi = OpenWRTWifi.OpenWRTWifi(self.database)
        
        # Set to start on boot w/ Cron if not already so
        
        
        atexit.register(self.__reset)
    
    
    def create_slice(self, slice, user, config):
        
        # Make sure slice does not already exist
        if slice in self.database.get_slice_list():
            raise exception.SliceCreationFailed("Slice " + slice  + " already exists!")
        
        # Create datbase entry
        self.database.create_slice(slice, user)
        self.database.set_active_slice(slice)
        
        # Parse config
        # Create all virtual interfaces
        for interfaces in config['VirtualInterfaces']:
            try:
                self.v_interfaces.create(interfaces["flavor"], interfaces["attributes"])
            except:
                # Abort, delete
                self.delete_slice(slice)
                raise exception.SliceCreationFailed("Aborting.\nVirtual Interface creation failed: " + interfaces['attributes']['name'])
                
        # Create all virtual bridges
        for bridges in config['VirtualBridges']:
            bridge_name = bridges['attributes']['name']
            try:
                self.v_bridges.create_bridge(bridges['flavor'], bridge_name)
            except:
                # Abort, delete
                self.delete_slice(slice)
                raise exception.SliceCreationFailed("Aborting.\nBridge creation failed: " + bridge_name)
            else:    
                # Bridge created, now apply the settings
                # Add ports
                for port in bridges['attributes']['interfaces']:
                    try:
                        self.v_bridges.add_port_to_bridge(bridge_name, port)
                    except:
                        # Abort, delete.
                        self.delete_slice(slice)
                        raise exception.SliceCreationFailed("Aborting.\nError adding port " + port + " to bridge " + bridge_name)
                
                # Bridge settings
                setting_list = bridges['attributes']['bridge_settings']
                for setting in setting_list:
                    try:
                        self.v_bridges.modify_bridge(bridge_name, setting, setting_list[setting])
                    except:
                        # Abort, delete. Settings don't matter when deleting
                        self.delete_slice(slice)
                        raise exception.SliceCreationFailed("Aborting.\nError applying setting " + setting + " to bridge " + bridge_name)
                    
                # Port settings
                for port in bridges['attributes']['port_settings']:
                    for setting in bridges['attributes']['port_settings'][port]:
                        try:
                            self.v_bridges.modify_port(bridge_name, port, setting, bridges['attributes']['port_settings'][port][setting])
                        except:
                            # Abort, delete
                            self.delete_slice(slice)
                            raise exception.SliceCreationFailed("Aborting.\nError applying setting " + setting + " to port " + port + " on bridge " + bridge_name)
                    
        self.database.reset_active_slice()        
        

    def delete_slice(self, slice):
        """Delete a given slice, and ignore any errors that occur in
        the process in case a slice is corrupted."""
        
        try:
            slice_data = self.database.get_slice_data(slice)
            self.database.set_active_slice(slice)
        except KeyError:
            # If slice does not exist, ignore
            pass
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
        { "module" : "VirtualInterfaces", "command" : "get_status", "args" : { "name" : "tap1"} }
        
        ***Temporarily: OpenWRTWifi module can now be used. ***"""
        
        
        self.database.set_active_slice(slice)
        if info["module"] == "VirtualInterfaces":
            command = getattr(self.v_interfaces, info["command"])
        elif info["module"] == "VirtualBridges":
            command = getattr(self.v_bridges, info["command"])
        elif info["module"] == "Database":
            command = getattr(self.database, info["command"])
        elif info["module"] == "OpenWRTWifi":
            command = getattr(self.wifi, info["command"])
        
        # This won't cause any 'undefined variable' issues
        # since the JSON is verified to satisfy one of 
        # the three above if statements earlier
        return command(**info["args"])
        
        self.database.reset_active_slice()
        
    
    def execute(self, slice, command, config=None, user="default_user"):
        # determine if create, delete or modify
        if command == "create_slice":
            self.create_slice(slice, user, config)
        elif command == "delete_slice":
            self.delete_slice(slice)
        elif command == "modify_slice":
            self.modify_slice(slice, config)
        elif command == "remote_API":
            # Only the remote API can return data
            return self.remote_API(slice, config)
        elif command == "restart":
            return self.restart()
        #elif command == "restart_aurora"
        #    self.restart_aurora()
        else:
            raise exception.CommandNotFound(command)
    
    
    def restart(self):
        # Restart machine (OS), but give time for aurora to send OK to manager
        subprocess.Popen(['sleep 5; reboot'], shell=True)
        return "RESTARTING"
        
    #def restart_aurora(self):
        #Executes script that waits 10 secs and then runs aurora
        #subprocess.Popen(["./start_in_10_sec.sh"])
        #sys.exit(0)
    
    def list_users(self):
        print(self.database.list_users())
    
    def list_users_full(self):
        print(self.database.list_users_full())
    
    def list_all(self):
        print(self.database.list_all())
    
    def list_slice(self, slice):
        print(self.database.list_slice_contents(slice))
        
    def __reset(self):
        # Clear out all slices
        for slice in self.database.get_slice_list():
            self.delete_slice(slice)
            
        # Execute any specific reset functions
        # Usually, these need to be executed AFTER we 
        # finish using the class to delete stuff
        self.v_bridges.reset()
        self.v_interfaces.reset()
    
