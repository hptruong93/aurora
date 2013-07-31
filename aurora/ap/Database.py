# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, sys, exception, pprint
class Database:
    """Generic database for all class data.
    Format:
    {
	"slice_name": {
		"section_name": [
			[
				"flavour",
				{
					"data1": "bla1",
					"data2": "bla2",
					"name": "unique_name"
			    }]]}
	}
	Every entry is expected to have a "name" field, unique on the device where 
	this code is run.  For a number of entries, interface names
	are a good choice.
	
	Note that no functions are provided to modify the fields in entries
	as the database does not know what entries contain beyond the requirement to
	have a slice, section, flavour and unique name, and thus cannot search for
	specific fields.  The user, however, can modify data without replacing
	entire entries by using get_entry, which provides a reference that can be
	modified."""
    
    INIT_DATABASE_FILE = "init_database.json"
    INIT_SLICE_USER_ID = "init_user-slice_database.json"
    DEFAULT_ACTIVE_SLICE = "default_slice"
    
    
    
    def __init__(self):
        # Create intial database from template
        self.database = json.load(open(self.INIT_DATABASE_FILE))
        self.user_id_data = json.load(open(self.INIT_SLICE_USER_ID))
        self.active_slice = self.DEFAULT_ACTIVE_SLICE
    
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
    
    def create_slice(self, slice, userid):
        """Create a new slice with a blank template."""
        # This is probably faster than using a template but having to do a deep copy
        self.database[slice] = { "VirtInterfaces": [], "VirtBridges": [] }
        # Create user ID entry if it does not exist
        if userid not in self.user_id_data:
            self.user_id_data[userid] = [slice]
        else:
            self.user_id_data[userid].append(slice)
    
    def delete_slice(self, slice):
        """Delete a slice and all associated information."""
        del self.database[slice]
        # Reset active slice to default if in use
        if self.active_slice == slice:
            self.reset_active_slice()
        # Find any instances in user list
        for user in self.user_id_data:
            # Trying to delete this slice from any user that does not have it
            # will produce an error, which we ignore.
            try:
                self.user_id_data[user].remove(slice)
            except ValueError:
                pass
        # TODO: Add cleanup function to delete empty users (is this necessary even?)
        
    def get_associated_slice(self, userid):
        return self.user_id_data[userid]
    
    def get_slice_data(self, slice):
        return self.database[slice]
    
    def add_entry(self, section, flavour, info):
        """Add an entry to the database.
        Names in each section must be unique, but different sections
        can have the same name."""
        # Complain if entry already exists
        try:
            self.get_entry(section, info["name"])
        except exception.EntryNotFound:
            # OK, does not exist
            self.database[self.active_slice][section].append([flavour, info])
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
            if entry[1]["name"] == name:
                return entry
        raise exception.EntryNotFound(name)
    
    def get_entry_search(self, name):
        """Returns the entry identified by name if it exists.
        Searches through the entire dictionary, rather than a single section.
        If multiple entries with the same name exist, only one will be returned.
        Raises exception.EntryNotFound if the entry does not exist."""
        # TODO: Speed this up?
        for section in self.database[self.active_slice]:
            # Faster than calling get_entry - it would redo dictionary
            # lookups unecessarily
            for entry in self.database[self.active_slice][section]:
                if entry[1]["name"] == name:
                    return entry
        raise exception.EntryNotFound(name)
        
        
    def list_slice_contents(self, slice):
        return pprint.pformat(self.database[slice])
        
    # TODO: Remove in production
    def get_database(self):
        """For debugging."""
        return pprint.pformat(self.database)
        
