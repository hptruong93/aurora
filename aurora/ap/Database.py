# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, sys, exception, pprint, copy
class Database:
    """Generic database for all class data.
    Format for slice data:
    {
	"slice_name": {
        "section": [
            {
                "some_attribute": {
                    "att1": "p1", 
                    "name": "p2"
                }, 
                "other_attribute": "veth"
            }, 
	}
	Every entry is expected to have a "name" field, unique on the device where 
	this code is run.  For a number of entries, interface names
	are a good choice.
	
	Note that no functions are provided to modify the fields in entries
	as the database does not know what entries contain beyond the requirement to
	have a slice, section, flavour and unique name, and thus cannot search for
	specific fields.  The user, however, can modify data without replacing
	entire entries by using get_entry, which provides a reference that can be
	modified.
	
	For the 'hardware' data, the format is different. Ex.:
	
	  {
      "firmware":"openwrt",
      "firmware_version":"r37630",
      "aurora_version":"0.1",
      "memory_mb":"256",
      "wifi_radio":
        {
            "number_radio":"1",
            "number_radio_free":"1",
            "radio_list":
                [
                    {
                        "name": "radio0",
                        "bss_list":[...]
                        }]}}
     
     The details of what goes in the  radio list
     is mostly left to whatever class uses it, but
     the minimum requirement is that each entry be a 
     dictionary with a name field that will be used to refer
     to the object.

	
	"""
    
    INIT_DATABASE_FILE = "init_database.json"
    INIT_SLICE_USER_ID = "init_user-slice_database.json"
    DEFAULT_ACTIVE_SLICE = "default_slice"
    DEFAULT_HW_DATABASE = "init_database_hardware.json"
    
    def __init__(self):
        # Create intial database from template
        self.database = json.load(open(self.INIT_DATABASE_FILE))
        self.user_id_data = json.load(open(self.INIT_SLICE_USER_ID))
        self.active_slice = self.DEFAULT_ACTIVE_SLICE
        
        self.hw_database = json.load(open(self.DEFAULT_HW_DATABASE))
    
    def set_active_slice(self, slice):
        """Set the active slice, used for commands such as
        add_entry or del_entry."""
        self.active_slice = slice
        
    def get_active_slice(self):
        """Returns the current active slice setting."""
        return self.active_slice
    
    def reset_active_slice(self):
        """Set the active slice back to the default slice."""
        self.active_slice = self.DEFAULT_ACTIVE_SLICE
        
    def add_slice_to_user(self, user, slice):
        """Add the given slice to the user, and create
        the user if he does not exist.  Slices already
        owned by the user are ignored."""
        # Create user if necessary
        if user not in self.user_id_data:
            self.create_user(user)
        # Do not append if already listed
        if slice not in self.user_id_data[user]:
            self.user_id_data[user].append(slice)
        
    def delete_slice_from_user(self, user, slice):
        """Delete the slice from the user.  Will
        silently ignore any errors such as the user not existing
        or the user not owning the slice."""
        # Ignore any errors when removing, as user/slice
        # may no longer exist
        try:
            self.user_id_data[user].remove(slice)
        except:
            pass
    
    def create_user(self, user):
        """Create the given user, but do nothing
        if he already exists."""
        # Don't want to overwrite existing user
        if user not in self.user_id_data:
            self.user_id_data[user] = []
    
    def delete_user(self, user):
        """Delete the given user, and ignore any
        errors such as the user not existing."""
        # Ignore any errors deleting
        try:
            del self.user_id_data[user]
        except:
            pass
    
    def create_slice(self, slice, userid):
        """Create a new slice with a blank template."""
        # This is probably faster than using a template but having to do a deep copy
        self.database[slice] = { "VirtualInterfaces": [], "VirtualBridges": [] }
        self.add_slice_to_user(userid, slice)
    
    def delete_slice(self, slice):
        """Delete a slice and all associated information."""
        del self.database[slice]
        # Reset active slice to default if in use
        if self.active_slice == slice:
            self.reset_active_slice()
        # Find any instances in user list
        for user in self.user_id_data:
            # Delete the slice
            self.delete_slice_from_user(user, slice)
        
    def get_associated_slice(self, userid):
        """Returns a list of slices associated to the userid."""
        # Using deepcopy; same reason as below
        return copy.deepcopy(self.user_id_data[userid])
    
    def get_slice_data(self, slice):
        """Returns a (deep) copy of the contents of the slice."""
        # Need deep copy because users may iterate over the list
        # while modifying the core database
        # Other functions should not need this, 
        # as they do not return data that is likely to be iterated
        # over and modified.  The closest that fits the bill 
        # is get_entry, but it needs to be accessible to 
        # allow for nested data modification.
        return copy.deepcopy(self.database[slice])
    
    def get_slice_list(self):
        """Return a list of slices."""
        return self.database.keys()
        
    def get_user_list(self):
        """Return a list of users."""
        return self.user_id_data.keys()
    
    def add_entry(self, section, flavour, info):
        """Add an entry to the database.
        Names in each section must be unique, but different sections
        can have the same name."""
        # Complain if entry already exists
        try:
            self.get_entry(section, info["name"])
        except exception.EntryNotFound:
            # OK, does not exist
            self.database[self.active_slice][section].append({ "flavor" : flavour, "attributes" : info })
        else:
            # Error
            raise exception.NameAlreadyInUse(info["name"])

    
    def delete_entry(self, section, name):
        """Remove an entry from the database."""
        try:
            entry = self.get_entry(section, name)
            self.database[self.active_slice][section].remove(entry)
        except:
            # Ignore any errors deleting
            pass
    
    def replace_entry(self, section, name, flavour, info):
        """A shortcut to deleting and adding an entry."""
        self.del_entry(section, name)
        self.add_entry(section, flavour, info)
    
    def get_entry(self, section, name):
        """Returns the entry identified by section and name
        if it exists.  Raises exception.EntryNotFound if it does not."""
        for entry in self.database[self.active_slice][section]:
            if entry["attributes"]["name"] == name:
                return entry
        raise exception.EntryNotFound(name)
    
    def get_entry_search(self, name):
        """Returns the entry identified by name if it exists.
        Searches through the entire dictionary (keeping to one slice), 
        rather than a single section.
        
        If multiple entries with the same name exist, only one will be returned.
        Raises exception.EntryNotFound if the entry does not exist."""
        # TODO: Speed this up?
        for section in self.database[self.active_slice]:
            # Faster than calling get_entry - it would redo dictionary
            # lookups unecessarily
            try:
                self.get_entry(section,name)
            except exception.EntryNotFound:
                # Ignore not finding in a specific section; only raise error
                # when not in any section
                pass
        raise exception.EntryNotFound(name)
        
        
    def list_slice_contents(self, slice, as_json=False):
        """Returns a formatted string showing the slice contents."""
        if as_json:
            return json.dumps(self.database[slice])
        else:
            return pprint.pformat(self.database[slice])
        
    def list_users(self, as_json=False):
        if as_json:
            return json.dumps(self.get_user_list())
        else:
            return pprint.pformat(self.get_user_list())
        
    def list_users_full(self, as_json=False):
        if as_json:
            return json.dumps(self.user_id_data)
        else:
            return pprint.pformat(self.user_id_data)
        
    def list_all(self, as_json=False):
        if as_json:
            return json.dumps(self.database)
        else:
            return pprint.pformat(self.database)
            
            
            
    def hw_get_firmware_name(self):
        """Returns the name of the firmware."""
        return self.hw_database["firmware"]
    
    def hw_set_firmware_name(self, firmware):
        """Sets the name of the firmware."""
        self.hw_database["firmware"] = firmware
    
    def hw_get_aurora_version(self):
        """Returns the aurora version."""
        return self.hw_database["aurora_version"]
        
    def hw_set_aurora_version(self, aurora):
        """Sets the aurora version.  Accepts a string."""
        self.hw_database["aurora_version"] = aurora
        
    def hw_get_memory_mb(self):
        """Returns the total RAM of the device."""
        return self.hw_database["memory_mb"]
        
    def hw_set_memory_mb(self, memory):
        """Sets the amount of the total RAM on the device."""
        self.hw_database["memory_mb"] = memory
        
    def hw_get_num_radio(self):
        """Returns the total number of physical radios."""
        return self.hw_database["wifi_radio"]["number_radio"]
        
    def hw_set_num_radio(self, radios):
        """Sets the total number of physical radios."""
        self.hw_database["wifi_radio"]["number_radio"] = radios
        
    def hw_get_num_radio_free(self):
        """Returns the number of free radios."""
        return self.hw_database["wifi_radio"]["number_radio_free"]
        
    def hw_set_num_radio_free(self, radios):
        """Sets the number of free radios."""
        self.hw_database["wifi_radio"]["number_radio_free"] = radios
    
    def hw_add_radio_entry(self, radio_info):
        """Add a radio entry with information given as a dictionary,
        which requires at least a name field with a string value."""
        self.hw_database["wifi_radio"]["radio_list"].append(radio_info)
        
    
    def hw_del_radio_entry(self, radio):
        """Deletes a radio entry identified by name."""
        try:
            self.hw_database["wifi_radio"]["radio_list"].remove(self.hw_get_radio_entry(radio))
        except:
            # Ignore any errors deleting
            pass
        
    def hw_get_radio_entry(self, radio):
        """Returns the entry identified by radio name
        if it exists.  Raises exception.EntryNotFound if it does not."""
        for entry in self.hw_database["wifi_radio"]["radio_list"]:
            if entry["name"] == radio:
                return entry
        raise exception.EntryNotFound(radio)
        
    def hw_list_all(self, as_json=False):
        if as_json:
            return json.dumps(self.hw_database)
        else:
            return pprint.pformat(self.hw_database)
        
