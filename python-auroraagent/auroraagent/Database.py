# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import json, sys, exception, pprint, copy
class Database:
    """Generic database for all class data.
    Format for slice data::

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
                ]
            }
        }

    Every entry is expected to have a "name" field, unique on the device where 
    this code is run.  For a number of entries, interface names
    are a good choice.
    
    Note that no functions are provided to modify the fields in entries
    as the database does not know what entries contain beyond the requirement to
    have a slice, section, flavor and unique name, and thus cannot search for
    specific fields.  The user, however, can modify data without replacing
    entire entries by using get_entry, which provides a reference that can be
    modified.
    
    For the 'hardware' data, the format is different. Ex.::
    
        {
            "firmware":"openwrt",
            "firmware_version":"r37630",
            "aurora_version":"0.1",
            "memory_mb":"256",
            "wifi_radio": {
                "number_radio":"1",
                "number_radio_free":"1",
                "radio_list": {
                    [
                        {
                            "name": "radio0",
                            "bss_list":[...]
                        }
                    ]
                }
            }
        }
     
    The details of what goes in the  radio list
    is mostly left to whatever class uses it, but
    the minimum requirement is that each entry be a 
    dictionary with a name field that will be used to refer
    to the object.
    
    """
    
    DEFAULT_RADIO = "radio0"

    def __init__(self, config):
        # Create intial database from template
        self.database = config["default_config"]["init_database"]
        if "init_database" in config.get("last_known_config", {}).keys():
            self.prev_database = config["last_known_config"]["init_database"]
        else:
            self.prev_database = {}
        self.user_id_data = config["default_config"]["init_user_id_database"]
        if "init_user_id_database" in config.get("last_known_config", {}).keys():
            self.prev_user_id_data = config["last_known_config"]["init_database"]
        else:
            self.prev_user_id_data = {}
        self.active_slice = config["default_config"]["default_active_slice"]
        self.DEFAULT_ACTIVE_SLICE = config["default_config"]["default_active_slice"]
        
        self.hw_database = config["default_config"]["init_hardware_database"]
    
    def backup_current_config(self):
        """Stores the current configuration in the backup 
        database, prev_database, prev_user_id_data.

        """
        self.prev_database = copy.deepcopy(self.database)
        self.prev_user_id_data = copy.deepcopy(self.user_id_data)

    def set_active_slice(self, slice):
        """Set the active slice, used for commands such as
        add_entry or delete_entry."""
        self.active_slice = slice
        
    def get_active_slice(self):
        """Returns the current active slice setting."""
        return self.active_slice
    
    def reset_active_slice(self):
        """Set the active slice back to the default slice."""
        self.active_slice = self.DEFAULT_ACTIVE_SLICE

    def find_main_slice(self, config=None, radio=DEFAULT_RADIO):
        """Searches through a given set of slice configurations
        for the slice containing the main_bss.

        :param dict config:
        :param str radio:
        :rtype: string

        """
        if config == None:
            config = dict(
                [(k,v) for (k,v) in self.database.iteritems() 
                    if k != "default_slice"]
            )
        for slice, attributes in config.iteritems():
            for item in attributes["RadioInterfaces"]:
                if item["flavor"] == "wifi_radio":
                    if item["attributes"]["name"] == radio:
                        return slice
        return None
    def add_slice_to_user(self, user, slice):
        """Add the given slice to the user, and create
        the user if he does not exist.  Slices already
        owned by the user are ignored."""
        # Create user if necessary
        if user not in self.user_id_data:
            self.create_user(str(user))
        # Do not append if already listed
        if slice not in self.user_id_data[str(user)]:
            self.user_id_data[str(user)].append(slice)
        
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
            self.user_id_data[str(user)] = []
    
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
        self.database[slice] = { "VirtualInterfaces": [], "VirtualBridges": [], "RadioInterfaces" : [] }
        self.add_slice_to_user(str(userid), slice)
    
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
        
    def get_associated_slice(self, userid, prev=False):
        """Returns a list of slices associated to the userid."""
        # Using deepcopy; same reason as below
        if prev:
            return copy.deepcopy(self.prev_user_id_data.get(userid))
        return copy.deepcopy(self.user_id_data[userid])
    
    def get_slice_data(self, slice, prev=False):
        """Returns a (deep) copy of the contents of the slice."""
        # Need deep copy because users may iterate over the list
        # while modifying the core database
        # Other functions should not need this, 
        # as they do not return data that is likely to be iterated
        # over and modified.  The closest that fits the bill 
        # is get_entry, but it needs to be accessible to 
        # allow for nested data modification.
        if prev:
            return copy.deepcopy(self.prev_database.get(slice, {}))
        return copy.deepcopy(self.database[slice])

    def get_slice_radio(self, slice):
        """Searches the database and returns the radio on which
        the slice in question is created.  If no radio can be
        found, SliceRadioNotFound is raised.

        :param string slice:
        :rtype: string
        :raises: exception.SliceRadioNotFound

        """
        radio_interfaces = self.database.get(slice, {}).get(
            "RadioInterfaces",[]
        )
        for interface in radio_interfaces:
            if interface.get("flavor") == "wifi_bss":
                return interface.get("attributes", {}).get(
                    "radio", None
                )
        raise exception.SliceRadioNotFound()
    
    def get_slice_list(self):
        """Return a list of slices."""
        return list(k for k in self.database.keys() if k != "default_slice")

    def get_slice_ssid_map(self):
        slice_name_and_ssid = {}
        for slice_id, slice_config in self.database.iteritems():
            for slice_radio_config in slice_config.get(
                        "RadioInterfaces", []
                    ):
                if slice_radio_config.get("flavor") == "wifi_bss":
                    slice_name_and_ssid[slice_id] = \
                        slice_radio_config.get("attributes", {}).get(
                            "name"
                        )
        return slice_name_and_ssid
        
    def get_user_list(self, prev=False):
        """Return a list of users."""
        if prev:
            return self.prev_user_id_data.keys()
        return self.user_id_data.keys()

    def get_slice_user(self, slice, prev=False):
        """Finds the user that owns a specific slice."""
        for userid in self.get_user_list(prev):
            for slice_ in self.get_associated_slice(userid, prev):
                if slice_ == slice:
                    return str(userid)
        raise exception.NoUserIDForSlice()
    
    def add_entry(self, section, flavor, info):
        """Add an entry to the database.
        Names in each section must be unique, but different sections
        can have the same name."""
        # Complain if entry already exists
        try:
            self.get_entry(section, info["name"])
        except exception.EntryNotFound:
            # OK, does not exist
            if section not in self.database[self.active_slice].keys():
                self.database[self.active_slice][section] = []
            self.database[self.active_slice][section].append({ "flavor" : flavor, "attributes" : info })
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
    
    def replace_entry(self, section, name, flavor, info):
        """A shortcut to deleting and adding an entry."""
        self.delete_entry(section, name)
        self.add_entry(section, flavor, info)
    
    def get_entry(self, section, name):
        """Returns the entry identified by section and name
        if it exists.  Raises exception.EntryNotFound if it does not."""
        if section in self.database[self.active_slice].keys():
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

    def hw_get_free_disk(self):
        """Returns the total RAM of the device."""
        return self.hw_database["free_disk"]
        
    def hw_set_free_disk(self, memory):
        """Sets the amount of the total RAM on the device."""
        self.hw_database["free_disk"] = memory
    
        
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
        
    def hw_get_max_bss_per_radio(self):
        """Returns the maximum number of bss allowed per radio
        on this device.  Often constrained by limitations arising
        from the underlying software or hardware."""
        return self.hw_database["wifi_radio"]["max_bss_per_radio"]
        
    def hw_set_max_bss_per_radio(self, bss):
        """Sets the maximum number of bss allowed per radio
        on this device.  Often constrained by limitations arising
        from the underlying software or hardware."""
        self.hw_database["wifi_radio"]["max_bss_per_radio"] = bss
    
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

    def hw_get_slice_id_on_radio(self, radio):
        """Determines which slices exist on a physical radio, and lists 
        them by slice_id.

        :rtype: list 

        """
        radio_entry = self.hw_get_radio_entry(radio)
        # print "radio_entry"
        # print radio_entry

        slice_name_and_ssid_map = self.get_slice_ssid_map()
        slice_ssid_and_name_map = dict([(v, k) for (k, v) in 
                slice_name_and_ssid_map.iteritems()])
        # print json.dumps(slice_name_and_ssid_map, indent=4)
        # print json.dumps(slice_ssid_and_name_map, indent=4)

        slice_id_on_radio = []
        for bss in radio_entry.get("bss_list", []):
            slice_id = slice_ssid_and_name_map.get(
                bss.get("name"), None
            )
            if slice_id is not None:
                slice_id_on_radio.append(slice_id)

        # print "slice_id_on_radio"
        # print slice_id_on_radio

        return slice_id_on_radio
        
