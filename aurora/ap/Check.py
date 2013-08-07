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
        if not ("VirtInterfaces" in config and "VirtBridges" in config):
            raise exception.InvalidConfig("Missing VirtInterfaces or VirtBridges")
        
        # Now go through interface section
        # Make sure each entry has 2 entries - flavour and info
        for interface in config["VirtInterfaces"]:
            if len(interface) != 2:
                raise exception.InvalidConfig("Bad entry in VirtInterfaces - " + str(interface) + " length not 2")
            # Not checking for specifics, only the presence of a name field
            if "name" not in interface[1]:
                raise exception.InvalidConfig("No name field in " + str(interface) + " detected.")
        
        # Bridge check
        for bridge in config["VirtBridges"]:
            if len(bridge) != 2:
                raise exception.InvalidConfig("Bad entry in VirtBridges - " + str(bridge) + " length not 2")
            # Check for main fields, since they are required among all bridges
            if not ("name" in bridge[1] and "interfaces" in bridge[1] and "bridge_settings" in bridge[1] and "port_settings" in bridge[1]):
                raise exception.InvalidConfig(str(bridge) + " is missing key field.")
        
    def modify_slice_check(self, config):
        # Check to make sure VirtBridges is the only entry
        if not (len(config) == 1 and "VirtBridges" in config):
            raise exception.InvalidConfig("VirtBridges must be the first and only entry.")
        # Make sure name, bridge_settings and port_settings exist
        bridge = config["VirtBridges"]
        if not ("name" in bridge and "bridge_settings" in bridge and "port_settings" in bridge):
            raise exception.InvalidConfig(str(bridge) + " is missing key field.")
        
    def remote_API_check(self, config):
        # Check for main fields
        if not("module" in config and "command" in config):
            raise exception.InvalidConfig("Missing key field in " + str(config))
        # If no argument specified, create blank one
        if not "args" in config:
            config["args"] = {}
        # Check module field - must be bridge or interface
        if not (config["module"] == "VirtInterfaces" or config["module"] == "VirtBridges"):
            raise exception.InvalidConfig("Module field must be either VirtInterfaces or VirtBridges.")

