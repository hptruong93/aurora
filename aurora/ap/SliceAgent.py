# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import VirtualBridges, VirtualInterfaces, exception, json, copy, pprint, Database
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
            
    
    # modify_slice slice_name SECTION COMMAND ARGS
    def modify_slice(self, slice, config):
        pass
        # Need to check section, command and then data
        #if slice not in self.slice_database
        #    raise exception.SliceNotFound(slice)
        #    
        #slice_info = self.load_mod_slice_info()
        
        
    def load_mod_slice_info(self):
        return json.load(open('slice_info.json'))
    
    def execute(self, slice, command, config=None):
        # determine if create, delete or modify
        if command == "create_slice":
            create_slice(slice, config)
        elif command == "delete_slice":
            delete_slice(slice)
        elif command == "modify_slice":
            modify_slice(slice, config)
        else:
            raise exception.CommandNotFound(command)
    
    
    def check_config(self, format, config):
        pass
    
    def list_all(self):
        pprint.pprint(self.slice_database)
    
    def list_slice(self, slice):
        pprint.pprint(self.slice_database[slice])
        
    def reset(self):
        pass
    
