# Virtual interface class: sets up, kills or configures virtual interfaces.
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import json, sys, exception, copy, atexit
class VirtualInterfaces:
    """Virtual Interface class.

    All commands relating to virtual interfaces directly should be directed to this class.
    It will handle any implementation or program specfic parameters necessary."""
    
    MODULE_JSON_FILE = 'modules.json'
    MODULES_FOLDER = 'modules'

    def __init__(self):
        # Create list of all interfaces and modules
        self.interface_list = {}
        self.module_list = {}
        # Load JSON.  Will raise an error if not found, but the code is useless
        # without it anyways....
        json_file = open(self.MODULE_JSON_FILE)
        self.metadata = json.load(json_file)
        
        # Cleanup on exit
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
        pid = running_flavour.start(**args)
        
        # Record it
        self.__add_entry(flavour, pid, args)
        
    
    def modify(self, name, args):
        """Change the parameters of a given interface."""
        # Get existing entry and flavour
        pid = self.__get_pid(name)
        entry = self.interface_list[pid]
        flavour = entry["flavour"]
        
        # Delete it, restart with new args
        self.delete(pid)
        return self.create(flavour,args)
         
    def delete(self, name):
        """Delete a given interface."""
        pid = self.__get_pid(name)
        
        entry = self.interface_list[pid]
        flavour = entry["flavour"]
        # Module should already be loaded
        manager = self.__get_module(flavour)
        manager.stop(pid)
        self.__del_entry(pid)
        
        # if no more instances of the module are active, remove module
        flavour_exists = False
        for i in self.interface_list:
            if self.interface_list[i]["flavour"] == flavour:
                flavour_exists = True
        
        if not flavour_exists:
            self.__unload_module(flavour)
        
    def show(self, name):
        """Show information about a specific interface."""
        pid = self.__get_pid(name)
        return str(self.interface_list[pid])
    
    def list(self):
        """List information about all PIDs."""
        return str(self.interface_list)
        
    def reset(self):
        """Wipes all configuration data and deletes any running interfaces."""
        for key in self.module_list:
            try:
                # This will wipe any instances, even if they are not in interface_list
                self.module_list[key].kill_all()
            except Exception:
                # Ignore any errors
                pass
        
        self.__clear_entries()
        self.__unload_all_modules()
        
    def get_status(self, pid):
        """Returns wehther or not a given instance is running."""
        # Get flavour -> get the associated module -> get status
        return self.module_list[self.interface_list[pid]["flavour"]].status(pid)
    
    def check_interface(self,pid):
        """Checks to see if an instance has died, and removes it if so."""
        status = self.get_status(pid)
        # False : not running
        if status == False :
            try:
                self.delete(pid)
            except Exception:
                # Delete the entry in case delete failed
                self.__del_entry(pid)
    
    def update_status_all(self):
        """Checks all instances, and removes any that have died."""
        # Deepcopying to prevent list modification during iteration
        for pid in copy.deepcopy(self.interface_list):
            self.check_interface(pid)
    
    def __get_pid(self, name):
        for pid in self.interface_list:
            if self.interface_list[pid]["arguments"]["name"] == name:
                return pid
        raise exception.PIDNotFound()
    
    def __add_entry(self, flavour, pid, arguments):
        # Do not want to overwrite if already existing
        if pid not in self.interface_list:
            self.interface_list[pid] = {"flavour" : flavour, "arguments" : arguments}
    
    def __del_entry(self, pid):
        try:
            del self.interface_list[pid]
        # If entry does not exist, ignore
        except KeyError:
            pass

    def __clear_entries(self):
        self.interface_list.clear()
        
