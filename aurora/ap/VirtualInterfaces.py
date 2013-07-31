# Virtual interface class: sets up, kills or configures virtual interfaces.
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, sys, exception, atexit
class VirtualInterfaces:
    """Virtual Interface class.

    All commands relating to virtual interfaces directly should be directed to this class.
    It will load appropriate modules to process any requests."""
    
    MODULE_JSON_FILE = 'modules.json'
    MODULES_FOLDER = 'modules'

    def __init__(self, database):
        # Create list of modules
        self.module_list = {}
        # Load JSON.  Will raise an error if not found, but the code is useless
        # without it anyways....
        json_file = open(self.MODULE_JSON_FILE)
        self.metadata = json.load(json_file)["VirtualInterfaces"]
        
        # Load database
        self.database = database
        
        # Remove virtual interfaces on exit
        atexit.register(self.reset)
        
    def __load_module(self, flavour):
        
        # Cast to string - some issues with unicode?
        flavour = str(flavour)
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
    
    
    def create(self, flavour, args):
        """Creates a virtual interface of the type (flavour) specified. Arguments
        (args) depend on the type and should be passed as a dictionary.
        
        Dictionary keys must match the variables accepted by the start function of
        the module. See the documentation on the modules (implemented as classes)
        for more information.
        
        Ex. If the module has a function start(bob,alice,charlie), the dictionary
        could be { charlie : 3, bob : 1, alice : 2 }."""
    
        # Check if flavour exists
        if flavour not in self.metadata:
            raise exception.FlavourNotExist(flavour)

        # Load flavour data
        running_flavour = self.__load_module(flavour)
        
        # Everything loaded; now create the interface
        # (Python unpacks arguments with **)
        running_flavour.start(**args)
        
        # Record it
        self.__add_entry(flavour, args)
        
    
    def modify(self, name, args):
        """Change the parameters of a given interface."""
        # Get existing entry and flavour
        entry = self.__get_entry(name)
        flavour = entry[0]
        
        # Delete it, restart with new args
        self.delete(name)
        self.create(flavour, args)
         
    def delete(self, name):
        """Delete a given interface."""
        
        entry = self.__get_entry(name)
        flavour = entry[0]
        # Module should already be loaded
        manager = self.__get_module(flavour)
        manager.stop(name)
        self.__del_entry(name)
        
    def get_status(self, name):
        """Returns whether or not a given instance is running."""
        # Get flavour -> get the associated module -> get status
        return self.module_list[self.__get_entry(name)[0]].status(name)
    
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
    
    def __add_entry(self, flavour, arguments):
        self.database.add_entry("VirtInterfaces", flavour, arguments)
    
    def __get_entry(self, name):
        return self.database.get_entry("VirtInterfaces", name)
    
    def __del_entry(self, name):
        self.database.delete_entry("VirtInterfaces", name)
        
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
        
