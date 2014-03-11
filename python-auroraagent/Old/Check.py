# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import exception
class Check:
    """This class is responsible for checking configuration files
    and confirming their validity.  It will raise exceptions
    if there are errors, although the user is free to
    catch them if so desired.  It will do nothing if the
    configuration is valid."""
    
    def create_slice_check(self, config):
        # Check that virtual interface and bridge sections exist
        if not ("VirtualInterfaces" in config and "VirtualBridges" in config):
            raise exception.InvalidConfig("Missing VirtualInterfaces or VirtualBridges")
        
        # Now go through interface section
        # Make sure each entry has attributes and flavour entry
        for interface in config["VirtualInterfaces"]:
            if not("attributes" in interface and "flavor" in interface):
                raise exception.InvalidConfig("Bad entry in VirtualInterfaces - " + str(interface) + " - missing flavor or attributes field.")
            # Not checking for specifics, only the presence of a name field
            if "name" not in interface["attributes"]:
                raise exception.InvalidConfig("No name field in " + str(interface) + " detected.")
        
        # Bridge check
        for bridge in config["VirtualBridges"]:
            if not("attributes" in bridge and "flavor" in bridge): 
                raise exception.InvalidConfig("Bad entry in VirtualBridges - " + str(bridge) + " - missing flavor or attributes field.")
            # Check for main fields, since they are required among all bridges
            if not ("name" in bridge["attributes"] and "interfaces" in bridge["attributes"] and "bridge_settings" in bridge["attributes"] and "port_settings" in bridge["attributes"]):
                raise exception.InvalidConfig(str(bridge) + " is missing key field.")
        
    def modify_slice_check(self, config):
        # Check to make sure VirtualBridges is the only entry
        if not (len(config) == 1 and "VirtualBridges" in config):
            raise exception.InvalidConfig("VirtualBridges must be the first and only entry.")
        # Make sure name, bridge_settings and port_settings exist
        bridge = config["VirtualBridges"]
        if not ("name" in bridge and "bridge_settings" in bridge and "port_settings" in bridge):
            raise exception.InvalidConfig(str(bridge) + " is missing key field.")
        
    def remote_API_check(self, config):
        # Check for main fields
        if not("module" in config and "command" in config):
            raise exception.InvalidConfig("Missing key field in " + str(config))
        # If no argument specified, create blank one
        if not "args" in config:
            config["args"] = {}
        # Check module field - must be bridge or interface or database
        if not (config["module"] == "VirtualInterfaces" or config["module"] == "VirtualBridges" or config["module"] == "Database" ):
            raise exception.InvalidConfig("Module field must be either VirtualInterfaces, VirtualBridges or Database")

