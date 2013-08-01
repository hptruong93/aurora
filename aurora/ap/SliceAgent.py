# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import VirtualBridges, VirtualInterfaces, exception, json, pprint, Database, atexit
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
        
        atexit.register(self.__reset)
    
    # TODO: remove this when done testing
    def load_json(self):
        JFILE = open('ap.json')
        return json.load(JFILE)
    
    
    # TODO: add JSON config checks
    def create_slice(self, slice, user, config):
        
        # Create datbase entry
        self.database.create_slice(slice, user)
        self.database.set_active_slice(slice)
        
        # Parse config
        # Create all virtual interfaces
        for interfaces in config['VirtInterfaces']:
            try:
                self.v_interfaces.create(interfaces[0], interfaces[1])
            except:
                # Abort, delete
                self.delete_slice(slice)
                print("Aborting.\nVirtual Interface creation failed: " + interfaces[1]["name"])
                raise
                
        # Create all virtual bridges
        for bridges in config['VirtBridges']:
            bridge_name = bridges[1]['name']
            try:
                self.v_bridges.create_bridge(bridges[0], bridge_name)
            except:
                # Abort, delete
                self.delete_slice(slice)
                print("Aborting.\nBridge creation failed: " + bridge_name)
                raise
            else:    
                # Bridge created, now apply the settings
                # Add ports
                for port in bridges[1]['interfaces']:
                    try:
                        self.v_bridges.add_port_to_bridge(bridge_name, port)
                    except:
                        # Abort, delete.
                        self.delete_slice(slice)
                        print("Aborting.\nError adding port " + port + " to bridge " + bridge_name)
                        raise
                
                # Bridge settings
                setting_list = bridges[1]['bridge_settings']
                for setting in setting_list:
                    try:
                        self.v_bridges.modify_bridge(bridge_name, setting, setting_list[setting])
                    except:
                        # Abort, delete. Settings don't matter when deleting
                        self.delete_slice(slice)
                        print("Aborting.\nError applying setting " + setting + " to bridge " + bridge_name)
                        raise
                    
                # Port settings
                for port in bridges[1]['port_settings']:
                    for setting in bridges[1]['port_settings'][port]:
                        try:
                            self.v_bridges.modify_port(bridge_name, port, setting, port[setting])
                        except:
                            # Abort, delete
                            self.delete_slice(slice)
                            print("Aborting.\nError applying setting " + setting + " to port " + port + " on bridge " + bridge_name)
                            raise
                    
        self.database.reset_active_slice()        
        
    # TODO: add JSON config checks
    # This will delete a slice, and ignore any errors while doing so
    # in case the slice has become corrupted.  We don't want to
    # prevent the user from deleting if something went wrong
    def delete_slice(self, slice):
        
        try:
            slice_data = self.database.get_slice_data(slice)
            self.database.set_active_slice(slice)
        except KeyError:
            # If slice does not exist, ignore
            pass
        else:   
            # Delete all bridges
            for bridge in slice_data['VirtBridges']:
                try:
                    self.v_bridges.delete_bridge(bridge[1]['name'])
                except:
                    print("Error: Unable to delete bridge " + bridge[1]['name'])
                    raise
            # Delete all virtual interfaces
            for interface in slice_data['VirtInterfaces']:
                try:
                    self.v_interfaces.delete(interface[1]['name'])
                except:
                    print("Error: Unable to delete virtual interface " + interface[1]['name'])
                    raise
                
        # Delete database entry
        self.database.delete_slice(slice)
        self.database.reset_active_slice()
            
    
    def modify_slice(self, slice, config):
        """The modify slice command will execute modify
        functions on various modules.  It will only execute commands
        that are not destructive or represent a significant
        topology change.  These include, but are not limited to,
        creating/deleting virtual interfaces, virtual bridges, or
        adding/deleting ports from bridges.
        
        At this time, this restricts the commands to port and 
        bridge modifications from the VirtualBridge module,
        with no support for port addition or deletion."""
        
        # Check to make sure VirtBridges is the only entry
        if not (len(config) == 1 and "VirtBridges" in config):
            raise exception.InvalidConfig()
        
        self.database.set_active_slice(slice)
        
        # Can do more than one bridge at once
        for entry in config["VirtBridges"]:
            data = config["VirtBridges"][1]
            name = data["name"]
            # Bridge settings
            for setting in data["bridge_settings"]:
                self.v_bridges.modify_bridge(name, setting, data["bridge_settings"][settiing])
            # Port settings
            for port in data["port_settings"]:
                for port_setting in data["port_settings"][port]:  
                    self.v_bridges.modify_port(name, port, port_setting, data["port_settings"][port][port_setting])
    
        self.database.reset_active_slice()
        
    def remote_API(self, slice, info):
        """The remote API command accepts a specially formatted JSON
        file containing a number of fields:
        1. module : either VirtBridges or VirtInterfaces
        2. command : the command to execute
        3. args : a dictionary containing named arguments
        appropriate to the command.
        For example, to execute the command get_status(tap1) in VirtualInterfaces,
        you would format info like so:
        { "module" : "VirtInterfaces", "command" : "get_status", "args" : { "name" : "tap1"} }"""
        
        if info["module"] == "VirtInterfaces":
            command = getattr(v_interfaces, info["command"])
            command(**info["args"])
        elif info["module"] == "VirtBridges":
            command = getattr(v_bridges, info["command"])
            command(**info["args"])
        else:
            raise exception.InvalidConfig("Module " + info["module"] " does not exist.")
        
    def load_mod_slice_info(self):
        return json.load(open('slice_info.json'))
    
    def execute(self, slice, command, config=None):
        # determine if create, delete or modify
        if command == "create_slice":
            self.create_slice(slice, config)
        elif command == "delete_slice":
            self.delete_slice(slice)
        elif command == "modify_slice":
            self.modify_slice(slice, config)
        elif command == "remote_API":
            self.remote_API(slice, config)
        else:
            raise exception.CommandNotFound(command)
    
    
    def check_config(self, format, config):
        pass
    
    def list_all(self):
        pprint.pprint(self.slice_database)
    
    def list_slice(self, slice):
        pprint.pprint(self.slice_database[slice])
        
    def __reset(self):
        # Clear out all slices
        for slice in self.database.get_slice_list():
            self.delete_slice(slice)
            
        # Execute any specific reset functions
        # Usually, these need to be executed AFTER we 
        # finish using the class to delete stuff
        self.v_bridges.reset()
        self.v_interfaces.reset()
    
