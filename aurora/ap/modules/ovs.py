# OpenVSwitch module
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

# If you wish to add functionaility for custom commands
# - say abstracting a long multi-parameter command to a simple one-argument function
# i.e. application do_something --with=1234 --output=test.db "file.test" -X
# to module.do_this(1234,test.db)
# Simply modify the modify_bridge and modify_port commands to properly parse
# and format the command line.  The current parsing is done as simple if statements,
# but more complicated cases (i.e. optional parameters) can easily be added.

import tempfile, subprocess, psutil, atexit
import exception
class OpenVSwitch:
    """OpenVSwitch module.  Controls the OpenVSwitch daemon, allowing
    for the creation and modification of bridges and their ports.
    Designed for OVS v 1.9.0"""
    
    # Change this to suit your environment.  Tested with
    # both OpenWRT (Attitude Adjustment w/ OVS from Julius Schulz-Zander)
    # and Ubuntu 13.04 w/ OVS 1.9 from apt
    ovs_schema = "/usr/share/openvswitch/vswitch.ovsschema"
    
    def __init__(self, database):
        self.database = database
        self.start()
        
        # Kill OVS when python closes
        atexit.register(self.stop)
    
    def __exec_command(self, args):
        # Want to throw exception if we give an invalid command
        # Note: args is a list of arguments
        # Format: [ arg1, arg2, arg3...]
        command = ["ovs-vsctl", "--db=unix:" + self.socket_file.name]
        command.extend(args)
        subprocess.check_call(command)
    
    def start(self):
        """Start required ovs daemons."""
        self.database_file = tempfile.NamedTemporaryFile()
        self.socket_file = tempfile.NamedTemporaryFile()
        # Close the files since we won't be writing to them
        # Also, tools like ovsdb-tool won't overwrite existing files
        # We are simply using temporary files to generate random names that don't conflict
        self.database_file.close()
        self.socket_file.close()

        # Create database in temporary file
        # Will raise exception if it fails
        subprocess.check_call(["ovsdb-tool", "create", self.database_file.name, self.ovs_schema])
       
        # Start ovs database server
        self.database_process = psutil.Popen(["ovsdb-server", "--remote=punix:" + 
        self.socket_file.name, self.database_file.name])
       
        # Start vswitchd
        self.vswitch_process = psutil.Popen(["ovs-vswitchd", "unix:" + self.socket_file.name])
       
    def stop(self):
        """Stop all OVS daemons."""
        # Kill vswitchd
        self.vswitch_process.terminate()
        self.vswitch_process.wait()
        
        # Kill database server
        self.database_process.terminate()
        self.database_process.wait()
        
        # Can't use close for database since it is already closed
        # Socket should already have been removed, but just in case
        try:
            os.remove(self.database_file.name)
        except Exception:
            pass
        
        try:
            os.remove(self.socket_file.name)
        except Exception:
            pass
    
    def create_bridge(self, bridge):
        """Create a bridge with the given name."""
        self.__exec_command(["add-br", bridge])
        # Bring bridge up
        subprocess.check_call(["ifconfig", bridge, "up"])
        
        self.database.add_entry("VirtBridges", "ovs", { "name" : bridge, "interfaces" : [], "bridge_settings" : {}, "port_settings" : {} })
    
    def delete_bridge(self, bridge):
        """Delete a bridge with the given name."""
        self.__exec_command(["del-br", bridge])
        self.database.delete_entry("VirtBridges", bridge)
    
    def modify_bridge(self, bridge, command, parameters=None):
        """Modifies a given bridge with the specified command and parameters.
        Some commands do not require any parameters, or it may be
        optional. These are marked with a *.  Generally, not specifying a command
        deletes the setting or resets it to default.
        Some commands require a dictionary of parameters in the format
        { arg1 : one, arg2: two, arg3: three }.
        These are marked with {dict}.
        Normally, parameters is simply a string.
        
        Commands        Parameters
        controller      controller*
        fail_mode       mode*"""
        
        
        # Find command, and format as appropriate
        if command == "controller":
            # Check if controller = 0.0.0.0, 0, None or 0 -> no controller
            if (parameters == None or  parameters == "0.0.0.0" or parameters == 0 or parameters == "0" ):
                args = [ "del-controller", bridge ]
                data_update = [ command, "0.0.0.0" ]
            else:
                args = [ "set-controller", bridge, parameters ]
                data_update = [ command, parameters ]
        elif command == "fail_mode":
            if (parameters == None):
                args = [ "del-fail-mode", bridge ]
                data_update = [ command, parameters ]
            else:
                args = [ "set-fail-mode", bridge, parameters ]
                data_update = [ command, parameters ]
        else:
            raise exception.CommandNotFound(command)
            
        self.__exec_command(args)
        # Update database
        entry = self.database.get_entry("VirtBridges", bridge)
        entry[1]["bridge_settings"][data_update[0]] = data_update[1]
    
    def add_port(self, bridge, port):
        """Add a port to the given bridge."""
        self.__exec_command(["add-port", bridge, port])
        entry = self.database.get_entry("VirtBridges", bridge)
        entry[1]["interfaces"].append(port)
    
    def delete_port(self, bridge, port):
        """Delete a port from the given bridge."""
        self.__exec_command(["del-port", bridge, port])
        entry = self.database.get_entry("VirtBridges", bridge)
        entry[1]["interfaces"].remove(port)
    
    def modify_port(self, bridge, port, command, parameters=None):
        """Not currently allowed."""
        # Not allowing any port modifications at this time
        # May change at a later date
        raise exception.CommandNotFound("No port modifications to OVS allowed.")
    
    def show(self):
        """Returns the output of the show command as a byte string."""
        # Need to get output, which is not provided by __exec_command
        return subprocess.check_output(["ovs-vsctl", "--db=unix:" + self.socket_file.name, "show"])
