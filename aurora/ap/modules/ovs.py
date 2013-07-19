# OpenVSwitch module
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

# If you wish to add functionaility for custom commands
# i.e. abstracting a long multi-parameter command to a simple one-argument function
# i.e. application do_something --with=1234 --output=test.db "file.test" -X
# to module.do_this(1234,test.db)
# Simply modify the modify_bridge and modify_port commands to properly parse
# and format the command line.  The current parsing is done as simple if statements,
# but more complicated cases (i.e. optional parameters) can easily be added.

import tempfile, subprocess, psutil
from .. import exception
class OpenVSwitch:
    """OpenVSwitch module.  Controls the OpenVSwitch daemon, allowing
    for the creation and modification of bridges and their ports.
    Designed for OVS v 1.9.0"""
    
    # Change this to suit your environment.  Tested with
    # both OpenWRT (Attitude Adjustment w/ OVS from Julius Schulz-Zander)
    # and Ubuntu 13.04 w/ OVS 1.9 from apt
    self.ovs_schema = "/usr/share/openvswitch/vswitch.ovschema"
    
    def __init__(self):
        self.start()
    
    
    def __exec_command(self, args):
        # Want to throw exception if we give an invalid command
        # Note: args is a list of arguments
        # Format: [ arg1, arg2, arg3...]
        command = ["ovs-vsctl"].extend(args)
        subprocess.check_call(command)
    
    def start(self):
        """Start required ovs daemons."""
        self.database = tempfile.NamedTemporaryFile()
        self.socket = tempfile.NamedTemporaryFile()

       # Create database in temporary file
       # Will raise exception if it fails
       subprocess.check_call(["ovsdb-tool", "create", database.name, self.ovs_schema])
       
       # Start ovs database server
       self.dabase_process = psutil.Popen(["ovsdb-server", "--remote=punix:" + 
        socket.name, database_file])
       
       # Start vswitchd
       self.vswitch_process = psutil.Popen(["ovs-vswitchd", "unix:" + socket.name])
       
    def stop(self):
        """Stop all OVS daemons."""
        # Kill vswitchd
        self.vswitch_process.terminate()
        self.vswitch_process.wait()
        
        # Kill database server
        self.database_process.terminate()
        self.database_process.wait()
        
        # Remove temp files
        self.socket.close()
        self.database.close()
    
    def create_bridge(self, bridge):
    """Create a bridge with the given name."""
    self.__exec_command(["add-br", bridge])
    
    def delete_bridge(self, bridge):
    """Delete a bridge with the given name."""
    self.__exec_command(["del-br", bridge])
    
    def modify_bridge(self, bridge, command, parameters=None):
        """Modifies a given bridge with the specified command and parameters.
        Parameters should be a dictionary.
        Ex. { arg1 : one, arg2: two, arg3: three }
        
        Allowed commands        Allowed arguments (required marked with *)
        set_controller          controller*
        del_controller                     
        set_fail_mode           mode*
        del_fail_mode"""
        
        # Find command, and format as appropriate
        if command == "set_controller":
            args = [ "set-controller", bridge, parameters["controller"] ]
        elif command == "del_controller":
            args = [ "del-controller", bridge ]
        elif command == "set_fail_mode":
            args = [ "set-fail-mode", bridge, parameters["mode"] ]
        elif command == "del_fail_mode":
            args = [ "del-fail-mode", bridge ]
        else
            raise exception.CommandNotFound()
            
        self.__exec_command(args)
    
    def add_port(self, bridge, port):
    """Add a port to the given bridge."""
    self.__exec_command(["add-port", bridge, port])
    
    def del_port(self, bridge, port):
    """Delete a port from the given bridge."""
    self.__exec_command(["del-port", bridge, port])
    
    def modify_port(self, bridge, port, parameters=None):
    """Not currently allowed."""
    # Not allowing any port modifications at this time
    # May change at a later date
    raise exception.CommandNotFound()
    
    def show(self):
    """Returns the output of the show command as a byte string."""
        # Need to get output, which is not provided by __exec_command
        return subprocess.check_output(["ovs-vsctl","show"])
