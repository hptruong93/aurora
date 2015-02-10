# Virtual Bridge class: configures virtual bridge programs.  
# Currently covers linux-bridge and OVS

# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, sys, exception, copy, os
import inspect

def ln(stringhere = 'was here', number_of_dash = 40):
    print("%s:%s %s> %s"% (__file__, inspect.currentframe().f_back.f_lineno, '-'*number_of_dash, stringhere))

class VirtualBridges:
    """Virtual Bridge class.

    All commands relating to virtual interfaces directly should be 
    directed to this class. It will handle any implementation or program 
    specfic parameters necessary."""
    
    MODULE_JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),'modules.json')
    MODULES_FOLDER = 'modules'

    def __init__(self, database):
        # Create list of modules
        self.module_list = {}
        # Load JSON.  Will raise an error if not found, but the code is useless
        # without it anyways....
        json_file = open(self.MODULE_JSON_FILE)
        self.metadata = json.load(json_file)["VirtualBridges"]
        json_file.close()
        self.database = database
        
    def __load_module(self, flavor):
        
        # Cast to string - some issues with unicode?
        flavor = str(flavor)
        # Try returning an existing module
        try:
            ln("initial bridge created")
            return self.__get_module(flavor)
        # If that fails, load it
        except exception.ModuleNotLoaded:
            ln("secondary bridge created")
            module_file = __import__(self.MODULES_FOLDER,globals(),locals(),
                    [flavor]).__dict__[flavor]
            module_class_name = self.metadata.get(flavor).get('class')
            module_class = getattr(module_file, module_class_name)
            module_instance = module_class(self.database)
            # Add to module list
            self.module_list[flavor] = module_instance
            # Give an instance
            return module_instance
    
    def __get_module(self,flavor):
        if flavor in self.module_list:
            return self.module_list[flavor]
        else:
            raise exception.ModuleNotLoaded(flavor)
    
    
    def __unload_module(self,flavor):
        try:
            del self.module_list[flavor]
        # If module not loaded, ignore
        except KeyError:
            pass
        
    def __unload_all_modules(self):
        self.module_list.clear()
    
    def __get_module_used(self, bridge):
        return self.module_list[self.__get_flavor(bridge)]
        
    def __get_flavor(self, bridge):
        return self.__get_entry(bridge)["flavor"]
    
    def create_bridge(self, flavor, name):
        """Create a bridge of type flavor and with the given name."""
        if flavor not in self.metadata:
            raise exception.FlavorNotExist(flavor)
        
        # Load module
        print "Loading module:",flavor
        program = self.__load_module(flavor)
        
        # Module should now be running and we can execute commands
        # The assumption is that we try and create a bridge before modifying one
        print "Creating bridge:",name,
        program.create_bridge(name)
        print "SUCCESS"
    
    def delete_bridge(self, name):
        """Delete a bridge 'name'."""
        
        module = self.__get_module_used(name)
        module.delete_bridge(name)

      
    def modify_bridge(self, bridge, command, parameters=None):
        """Execute a command on the bridge that modifies it.
        The user is responsible for properly formatting the command
        and parameters."""
        # All sanity checking is assumed to be done by the module
        # At this level, we do not know what commands are valid or not
        module = self.__get_module_used(bridge)
        module.modify_bridge(bridge, command, parameters)
        
    def modify_port(self, bridge, port, command, parameters=None):
        """Execute a command on a port on a bridge that modifies it.
        The user is responsible for properly formatting the command
        and parameters."""
        # All sanity checking is assumed to be done by the module
        # At this level, we do not know what commands are valid or not
        module = self.__get_module_used(bridge)
        module.modify_port(bridge, port, command, parameters)
            
    def add_port_to_bridge(self, bridge, port):
        """Add a port to the specified bridge."""
        # Find module associated with bridge
        module = self.__get_module_used(bridge)
        
        # Any bad input will be handled by the module
        # Usually the base program will send a non-zero return code
        # which will in turn raise an exception (i.e. port does not exist)
        module.add_port(bridge, port)
    
    def delete_port_from_bridge(self, bridge, port):
        """Delete a port from the specified bridge."""
        # Find module associated with bridge, delete
        module = self.__get_module_used(bridge)
        module.delete_port(bridge, port)
    
    
    def list(self):
        """Retrieves and returns detailed information from the modules.
        Usually, this information will be direct from the managing program."""
        # Go through each module, and get info
        info = ""
        for flavor in self.module_list:
            info += ("flavor: " + flavor + "\n")
            info += self.module_list[flavor].show()
        
        return info
        
    def __get_entry(self, name):
        return self.database.get_entry("VirtualBridges", name)
        
    def reset(self):
        """Stops any running bridges.  Note that this may not delete
        bridges, especially for kernel built-in bridges like
        the standard linux-bridge module, where the stop function
        does nothing."""
        for key in self.module_list:
            try:
                self.module_list[key].stop()
            except Exception:
                # Ignore any errors
                pass
        self.__unload_all_modules()

