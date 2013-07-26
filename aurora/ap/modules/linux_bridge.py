# Linux bridge module
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

# If you wish to add functionaility for custom modify type commands
# i.e. abstracting a long multi-parameter command to a simple one-argument function
# i.e. application do_something --with=1234 --output=test.db "file.test" -X
# to module.do_this(1234,test.db)
# Simply modify the modify_bridge and modify_port commands to properly parse
# and format the command line.  The current parsing is done as simple if statements,
# but more complicated cases (i.e. optional parameters) can easily be added.

import subprocess
import exception

class Brctl:
    """Linux bridge module
    Controls the default bridge module that operates in the kernel,
    normally controlled with the brctl command.
    Note that brctl options may vary with the shell used; this program
    is designed to configure only the basics offered with the 
    busybox v.1.19.4 implementation, although it may work
    with other implementations without issue."""
    
    def __exec_command(self, args):
        # Want to throw exception if we give an invalid command
        # Note: args is a list of arguments
        # Format: [ arg1, arg2, arg3...]
        command = ["brctl"]
        command.extend(args)
        subprocess.check_call(command)
    
    def __init__(self):
        pass
    
    def start(self):
    # Nothing to start
        pass
    
    def stop(self):
    # Nothing to do
        pass
    
    def create_bridge(self, name):
        """Create a bridge with the given name."""
        self.__exec_command(["addbr",name])
        # Bring bridge up
        subprocess.check_call(["ifconfig", name, "up"])
    
    def delete_bridge(self,name):
        """Delete a bridge with the given name."""
        # Bridge must be brought down first
        # Ignoring any errors for ifconfig
        subprocess.call(["ifconfig", name, "down"])
        self.__exec_command(["delbr",name])
        
    def add_port(self, bridge, interface):
        """Add a port to the given bridge."""
        self.__exec_command(["addif", bridge, interface])
    
    def delete_port(self, bridge, interface):
        """Delete a port from the given bridge."""
        self.__exec_command(["delif", bridge, interface])

    def modify_bridge(self, bridge, command, parameters=None):
        """Modifies a given bridge with the specified command and parameters.
        Some commands do not require any parameters, or it may be
        optional. These are marked with a *.  Generally, not specifying a command
        deletes the setting or resets it to default.
        Some commands require a dictionary of parameters in the format
        { arg1 : one, arg2: two, arg3: three }.
        These are marked with {dict}.
        Normally, parameters is simply a string.
        
        Commands                Parameters
        ageing                  age
        forward_delay           delay
        hello_time              time
        max_age                 age
        bridge_priority         priority
        stp                     setting (string "on" or "off")"""
        
        if command == "ageing":
            args = [ "setageing", bridge, parameters ]
        elif command == "forward_delay":
            args = [ "setfd", bridge, parameters ]
        elif command == "hello_time":
            args = [ "sethello", bridge, parameters ]
        elif command == "max_age":
            args = [ "setmaxage", bridge, parameters ]
        elif command == "bridge_priority":
            args = [ "setbridgeprio", bridge, parameters ]
        elif command == "stp":
            args = [ "stp", bridge, parameters ]
        else:
            raise exception.CommandNotFound()
        
        self.__exec_command(args)
        
        
    def modify_port(self, bridge, port, command, parameters=None):
        """Modifies a given port with the specified command and parameters.
        Parameters should be a dictionary.
        Ex. { arg1 : one, arg2: two, arg3: three }
        
        Allowed commands        Allowed arguments (required marked with *)
        priority                priority*"""
        
        # Find command, and format as appropriate
        # busybox bridge command (1.19.4) seems to have an error in the help file
        # it specifies: setportprio BRIDGE PRIO		Set port priority
        # which produces a segmentation fault.  The command that does not return 
        # an error is setportprio BRIDGE PORT PRIO
        if command == "priority":
            args = [ "setportprio", bridge, port, parameters["priority"] ]
        else:
            raise exception.CommandNotFound()
        
        self.__exec_command(args)
        
    def show(self):
        """Returns the output of the show command as a byte string."""
        # Need to get output, which is not provided by __exec_command
        return subprocess.check_output(["brctl","show"])

    
        
        

