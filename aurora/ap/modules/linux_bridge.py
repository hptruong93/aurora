"""Linux bridge module
Controls the default bridge module that operates in the kernel,
normally controlled with the brctl command.
Note that brctl options may vary with the shell used; this program
is designed to configure only the basics offered with the 
busybox v.1.19.4 implementation, although it may work
with other implementations without issue."""
import subprocess

class brctl:
    
    def __exec_command(self, args)
        # Want to throw exception if we give an invalid command
        # Note: args is a list of arguments
        # Format: [ arg1, arg2, arg3...]
        command = ["brctl"].extend(args)
        subprocess.check_call(command)
    
    def add_bridge(self, name):
        """Create a bridge with the given name."""
        self.__exec_command(["addbr",name])
    
    def del_bridge(self,name):
        """Delete a bridge with the given name."""
        self.__exec_command(["delbr",name])
        
    def add_interface(self, bridge, interface):
        """Add an interface to the given bridge."""
        self.__exec_command(["addif", bridge, interface])
    
    def delete_interface(self, bridge, interface):
        """Delete an interface from the given bridge."""
        self.__exec_command(["delif", bridge, interface])

    def set_ageing(self, bridge, time):
        """Set the ageing time of the bridge."""
        self.__exec_command(["setageing", bridge, time])
    
    def set_forward_delay(self, bridge, delay):
        """Set the forward delay for the bridge."""
        self.__exec_command(["setfd", bridge, delay])
    
    def set_hello(self, bridge, time):
        """Set the hello time for the bridge."""
        self.__exec_command(["sethello", bridge, time])
        
    def set_max_age(self, bridge, age):
        """Set the maximum age for the bridge."""
        self.__exec_command(["setmaxage", bridge, age)
        
    def show(self)
        """Returns the output of the show command as a byte string."""
        # Need to get output, which is not provided by __exec_command
        return subprocess.check_output(["brctl","show"])
    
    def set_path_cost(self, bridge, cost):
        """Sets the path cost of the bridge."""
        self.__exec_command(["setpathcost", bridge, cost)
        
    # busybox bridge command (1.19.4) seems to have an error in the help file
    # it specifies: setportprio BRIDGE PRIO		Set port priority
    # which produces a segmentation fault.  The command that does not return an error
    # is setportprio BRIDGE PORT PRIO
    def set_port_priority(self, bridge, port, prio):
        """Set the prority of a port on a given bridge."""
        self.__exec_command(["setportprio", bridge, port, prio])
    
    def set_bridge_prority(self, bridge, prio):
        """Sets the prority of an entire bridge."""
        self.__exec_command(["setbridgeprio", bridge, prio])
        
    def spanning_tree_protocol(self, bridge, setting):
        """Enables or disables the spanning tree protocol on a bridge.
        Valid values for the setting parameter are 1,yes,on,0,no,off."""
        self.__exec_command(["stp", bridge, setting])
        

