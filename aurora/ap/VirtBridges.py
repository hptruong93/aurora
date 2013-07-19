# Virtual Bridge class: configures virtual bridge programs.  
# Currently covers linux-bridge and OVS

# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, sys, exception, pprint, copy
class VirtInterfaces:
    """Virtual Bridge class.

    All commands relating to virtual interfaces directly should be 
    directed to this class. It will handle any implementation or program 
    specfic parameters necessary."""
    
    MODULE_JSON_FILE = 'modules.json'
    MODULES_FOLDER = 'modules'

    def __init__(self):
        # Create list of all virtual bridges and modules
        self.bridge_list = {}
        self.module_list = {}
        # Load JSON.  Will raise an error if not found, but the code is useless
        # without it anyways....
        json_file = open(self.MODULE_JSON_FILE)
        self.metadata = json.load(json_file)
        
    def __load_module(self, flavour):
        
        # Try returning an existing module
        try:
            return self.__get_module(flavour)
        # If that fails, load it
        except exception.ModuleNotLoaded:
            module_file = __import__(self.MODULES_FOLDER,globals(),locals(),
                    [flavour]).__dict__[flavour]
            module_class_name = self.metadata.get(flavour).get('class')
            module_class = getattr(module_file, module_class_name)
            module_instance = module_class()
            # Add to module list
            self.module_list[flavour] = module_instance
            # Give an instance
            return module_instance
    
    def __get_module(self,flavour):
        if flavour in self.module_list:
            return self.module_list[flavour]
        else:
            raise exception.ModuleNotLoaded(flavour)
    
    
    def __unload_module(self,flavour):
        try:
            del self.module_list[flavour]
        # If module not loaded, ignore
        except KeyError:
            pass
        
    def __unload_all_modules(self):
        self.module_list.clear()
        
    # Function list
    # __init__ : define lists
    # create_bridge()
    # del_bridge()
    # add_port_to_bridge()
    # del_port_from_bridge()
    # modify_bridge()
    # modify_port()
    # show
    
    def create_bridge(self, flavour, name):
        
        if flavour not in self.metadata:
            raise exception.FlavourNotExist(flavour)
        
        # Load module
        program = __load_module(self, flavour)
        
        # Module should now be running and we can execute commands
        # The assumption is that we try and create a bridge before modifying one
        program.create_bridge(name)
        
        # Record the bridge creation
        self.__add_entry(flavour, name)
    
    def delete_bridge(self, name):
        
    
    def __add_entry(self, flavour, name):
        # Do not want to overwrite if already existing
        # Name has to be unique
        if name not in self.bridge_list:
            self.bridge_list[name] = {"flavour" : flavour, "ports" : [] ,
                "settings" : {} }
    
    def __add_setting(self, name, setting, value):
        # Do not want to overwrite if already existing
        if name not in self.bridge_list:
            self.bridge_list[name]["settings"][setting] = value
            
    def __del_setting(self, name, setting):
        try:
            del self.bridge_list[name]["settings"][setting]
        # If entry does not exist, ignore
        except KeyError:
            pass
    
    def __del_entry(self, name):
        try:
            del self.bridge_list[name]
        # If entry does not exist, ignore
        except KeyError:
            pass

    def __clear_entries(self):
        self.bridge_list.clear()
       
    
    
        
