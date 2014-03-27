# Virtual interface class: sets up, kills or configures virtual interfaces.
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, sys, exception, os
class VirtualInterfaces:
    """Virtual Interface class.

    All commands relating to virtual interfaces directly should be directed to this class.
    It will load appropriate modules to process any requests."""
    
    MODULE_JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),'modules.json')
    MODULES_FOLDER = 'modules'

    def __init__(self, database):
        # Create list of modules
        self.module_list = {}
        # Load JSON.  Will raise an error if not found, but the code is useless
        # without it anyways....
        json_file = open(self.MODULE_JSON_FILE)
        self.metadata = json.load(json_file)["VirtualInterfaces"]
        json_file.close()
        
        # Load database
        self.database = database
        
    def __load_module(self, flavor):
        
        # Cast to string - some issues with unicode?
        flavor = str(flavor)
        # Try returning an existing module
        try:
            return self.__get_module(flavor)
        # If that fails, load it
        except exception.ModuleNotLoaded:
            module_file = __import__(self.MODULES_FOLDER,globals(),locals(),
                    [flavor]).__dict__[flavor]
            module_class_name = self.metadata.get(flavor).get('class')
            module_class = getattr(module_file, module_class_name)
            module_instance = module_class()
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
    
    
    def create(self, flavor, args):
        """Creates a virtual interface of the type (flavor) specified. Arguments
        (args) depend on the type and should be passed as a dictionary.
        
        Dictionary keys must match the variables accepted by the start function of
        the module. See the documentation on the modules (implemented as classes)
        for more information.
        
        Ex. If the module has a function start(bob,alice,charlie), the dictionary
        could be { charlie : 3, bob : 1, alice : 2 }."""
    
        # Check if flavor exists
        if flavor not in self.metadata:
            raise exception.FlavorNotExist(flavor)

        # Load flavor data
        running_flavor = self.__load_module(flavor)
        
        # Everything loaded; now create the interface
        # (Python unpacks arguments with **)
        running_flavor.start(**args)
        
        # Record it
        self.__add_entry(flavor, args)
        
    
    def modify(self, name, args):
        """Change the parameters of a given interface."""
        # Get existing entry and flavor
        entry = self.__get_entry(name)
        flavor = entry["flavor"]
        
        # Delete it, restart with new args
        self.delete(name)
        self.create(flavor, args)
         
    def delete(self, name):
        """Delete a given interface."""
        
        entry = self.__get_entry(name)
        flavor = entry["flavor"]
        # Module should already be loaded
        manager = self.__get_module(flavor)
        manager.stop(name)
        self.__del_entry(name)
        
    def get_status(self, name):
        """Returns whether or not a given instance is running."""
        # Get flavor -> get the associated module -> get status
        return self.module_list[self.__get_entry(name)["flavor"]].status(name)
    
    def check_interface(self, name):
        """Checks to see if an instance has died, and removes it if so."""
        status = self.get_status(name)
        # False : not running
        if status == False :
            try:
                self.delete(name)
            except Exception:
                # Delete the entry alone in case delete failed
                self.__del_entry(name)
    
    def __add_entry(self, flavor, arguments):
        self.database.add_entry("VirtualInterfaces", flavor, arguments)
    
    def __get_entry(self, name):
        return self.database.get_entry("VirtualInterfaces", name)
    
    def __del_entry(self, name):
        self.database.delete_entry("VirtualInterfaces", name)
        
    def reset(self):
        """Deletes any running virtual interfaces."""
        for key in self.module_list:
            try:
                # This will wipe any instances, even if they are not in the database
                self.module_list[key].kill_all()
            except Exception:
                # Ignore any errors
                pass
        self.__unload_all_modules()
        
