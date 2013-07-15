# Virtual interface class: sets up, kills or configures virtual interfaces.
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json
import sys
class VirtInterfaces:
    """ Virtual Interface class.

    All commands relating to virtual interfaces directly should be directed to this class.
    It will handle any implementation or program specfic parameters necessary."""
    
    MODULE_JSON_FILE = 'modules.json'
    MODULES_FOLDER = 'modules'

    def __init__(self):
        # Create list of all interfaces
        self.interface_list = {}
        # Load JSON.  Will raise an error if not found, but the code is useless
        # without it anyways....
        json_file = open(self.MODULE_JSON_FILE)
        self.metadata = json.load(json_file)
        
    def __load_module(self, flavour)
        module_file = __import__(self.MODULES_FOLDER,globals(),locals(),
                [flavour]).__dict__[flavour]
        module_class_name = self.metadata.get(flavour).get('class')
        module_class = getattr(module_file, module_class_name)
        module_instance = module_class()
        return module_instance
    
    
    def create(self, flavour, args):
        """Creates a virtual interface of the type specified. Arguments depend on the type 
        and should be passed as a dictionary.
        
        See the documentation on the classes (modules) for more information
        on the arguments.
        """
    
        # Check if flavour exists
        if flavour not in self.metadata:
            raise Exception("Flavour" + flavour + "does not exist!")
        else:
            # Load flavour data
            running_flavour = __load_module(flavour)
        
        # Everything loaded; now create the interface
        # Arguments specified in metadata
        #running_flavour.
    
    #if instance == "capsulator": 
    #    pid = caps.start(args.get(tunnel_interface), args.get(forward_to), args.get(border_interface))
    #    __add_entry("capsulator", pid, args)
    #    
    #elif instance == "veth":
    #    vethd.start(args.get(real), args.get(virtual))
    #    __add_entry("veth", pid, args)
    #    
    
    def modify(self):
        pass
    def delete(self):
        pass
    def restart(self):
        pass
    def show(self):
        pass
    def list(self):
        pass
    def reset(self):
        """Wipes all configuration data and deletes any running interfaces."""
        pass
    def __add_entry(self, instance, pid, parameters):
        pass
    def __del_entry(self):
        pass
    def __mod_entry(self):
        pass
    def __clear_entries():
        pass
