# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import VirtualBridges, VirtualInterfaces, exception, json, copy
class SliceAgent:
    """The Slice Agent is the high level interface to the creation,
    modification and deletion of slices."""
    
    # Note: at lower levels, we throw exceptions around or 
    # simply ignore some errors (i.e. deleting a bridge
    # that does not exist).  At this level, we still ignore
    # some errors, like deleting a non-existent bridge
    # in some cases, but we start printing error messages
    # rather than raising exceptions and halting execution.
    # At so
    
    # Network class will receive packet -> decode ->
    # send command and config to this class
    
    def __init__(self):
        self.slice_database = {}
        # Init sub classes
        self.v_bridges = VirtualBridges.VirtualBridges()
        self.v_interfaces = VirtualInterfaces.VirtualInterfaces()
    
    # TODO: remove this when done testing
    def load_json(self):
        JFILE = open('ap.json', 'r')
        return json.load(JFILE)
    
    
    # TODO: delete all raises and print nice messages
    def create_slice(self, slice, config):
        
        # Create datbase entry (avoid reference issues)
        self.slice_database[slice] = copy.deepcopy(config)
        
        # Parse config
        # Create all virtual interfaces
        for interfaces in config['VirtInterfaces']:
            try:
                self.v_interfaces.create(interfaces[0], interfaces[1])
            except:
                # Delete entry if creation fails
                self.slice_database[slice]['VirtInterfaces'].remove(interfaces)
                print("Virtual Interface creation failed: " + interfaces[1]["name"])
                raise
                
        # Create all virtual bridges
        for bridges in config['VirtBridges']:
            bridge_name = bridges[1]['name']
            
            try:
                self.v_bridges.create_bridge(bridges[0], bridge_name)
            except:
                # Delete entry if creation fails
                self.slice_database[slice]['VirtBridges'].remove(bridges)
                print("Bridge creation failed: " + bridge_name)
                raise
            else:    
                # Bridge created, now apply the settings
                bridge_data_entry = self.slice_database[slice]['VirtBridges'][config['VirtBridges'].index(bridges)]
                # Add ports
                for port in bridges[1]['interfaces']:
                    try:
                        self.v_bridges.add_port_to_bridge(bridge_name, port)
                    except:
                        bridge_data_entry[1]['interfaces'].remove(port)
                        print("Error adding port " + port + " to bridge " + bridge_name)
                        raise
                
                setting_list = bridges[1]['bridge_settings']
                # Bridge settings
                for setting in setting_list:
                    try:
                        self.v_bridges.modify_bridge(bridge_name, setting, setting_list[setting])
                    except:
                        del bridge_data_entry[1]['bridge_settings'][setting]
                        print("Error applying setting " + setting + " to bridge " + bridge_name)
                        raise
                    
                # Port settings
                for port in bridges[1]['port_settings']:
                    for setting in port:
                        try:
                            self.v_bridges.modify_port(bridge_name, port, setting, port[setting])
                        except:
                            del bridge_data_entry[1]['port_settings'][port][setting]
                            print("Error applying setting " + setting + " to port " + port + " on bridge " + bridge_name)
                            raise
                    
            
        
    # TODO: delete raises, make nice error printing
    def delete_slice(self, slice):
        
        # Make sure key exists
        if slice in self.slice_database :       
            # Delete all bridges
            for bridge in self.slice_database[slice]['VirtBridges']:
                try:
                    self.v_bridges.delete_bridge(bridge[1]['name'])
                except:
                    print("Error: Unable to delete bridge " + bridge[1]['name'])
                    raise
            # Delete all virtual interfaces
            for interface in self.slice_database[slice]['VirtInterfaces']:
                try:
                    self.v_interfaces.delete(interface[1]['name'])
                except:
                    print("Error: Unable to delete virtual interface " + interface[1]['name'])
                    raise
                
            # Delete entry
            del self.slice_database[slice]
            
        # Do nothing if key does not exist - likely already deleted
            
    
    def modify_slice(self, slice, config):
        pass
    
    def execute(self, slice, command, config=None):
        # determine if create, delete or modify
        if command == "create_slice":
            create_slice(slice, config)
        elif command == "delete_slice":
            delete_slice(slice)
        elif command == "modify_slice":
            modify_slice(slice, config)
        else:
            raise exception.CommandNotFound()
    
    def list_all(self):
        pass
    
    def list_slice(self, slice):
        pass
        
    def reset(self):
        self.v_bridges.reset()
        self.v_interfaces.reset()
    
    
    
