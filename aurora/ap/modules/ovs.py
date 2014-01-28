# OpenVSwitch module
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

# If you wish to add functionaility for custom commands
# - say abstracting a long multi-parameter command to a simple one-argument function
# i.e. application do_something --with=1234 --output=test.db "file.test" -X
# to module.do_this(1234,test.db)
# Simply modify the modify_bridge and modify_port commands to properly parse
# and format the command line.  The current parsing is done as simple if statements,
# but more complicated cases (i.e. optional parameters) can easily be added.

import tempfile, subprocess, psutil, os
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
    
    def __exec_command(self, args):
        # Want to throw exception if we give an invalid command
        # Note: args is a list of arguments
        # Format: [ arg1, arg2, arg3...]
        command = ["ovs-vsctl", "--db=unix:" + self.socket_file.name]
        command.extend(args)
        print "\n  $ "," ".join(command)
        subprocess.check_call(command)
    
    def start(self):
        """Start required ovs daemons."""
        self.database_file = open(tempfile.NamedTemporaryFile().name + '1','w')
        self.socket_file = open(tempfile.NamedTemporaryFile().name + '1','w')
        print self.database_file
        print self.socket_file
        # Close the files since we won't be writing to them
        # Also, tools like ovsdb-tool won't overwrite existing files
        # We are simply using temporary files to generate random names that don't conflict
        self.database_file.close()
        self.socket_file.close()

        # Create database in temporary file
        # Will raise exception if it fails
        command = ["ovsdb-tool", "create", self.database_file.name, self.ovs_schema]
        print "\n  $ "," ".join(command)
        subprocess.check_call(["ovsdb-tool", "create", self.database_file.name, self.ovs_schema])
       
        # Start ovs database server
        command = ["ovsdb-server", "--remote=punix:" + 
                                                self.socket_file.name, self.database_file.name]
        print "\n  $ "," ".join(command)
        self.database_process = psutil.Popen(["ovsdb-server", "--remote=punix:" + 
                                                self.socket_file.name, self.database_file.name])
       
        # Start vswitchd
        command = ["ovs-vswitchd", "unix:" + self.socket_file.name]
        print "\n  $ "," ".join(command)
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
            print "Removing ovs_db", self.database_file.name
            os.remove(self.database_file.name)
        except Exception:
            print "...doesn't exist"
            #pass
        
        try:
            print "Removing ovs_socket", self.database_file.name
            os.remove(self.socket_file.name)
        except Exception:
            print "...doesn't exist"
            #pass
    
    def create_bridge(self, bridge):
        """Create a bridge with the given name."""
        self.__exec_command(["add-br", bridge])
        # Bring bridge up
        command = ["ifconfig", bridge, "up"]
        print "\n  $ "," ".join(command)
        subprocess.check_call(["ifconfig", bridge, "up"])
        
        self.database.add_entry("VirtualBridges", "ovs", { "name" : bridge, "interfaces" : [], "bridge_settings" : {}, "port_settings" : {} })
    
    def delete_bridge(self, bridge):
        """Delete a bridge with the given name."""
        self.__exec_command(["del-br", bridge])
        self.database.delete_entry("VirtualBridges", bridge)
    
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
        fail_mode       mode*
        ip              IP address*
        dpid            DPID value*"""
        
        # By default, ovs command
        ovs_command = True
        
        # Find command, and format as appropriate
        if command == "controller":
            # Check if controller = 0.0.0.0, 0, None or 0 -> no controller
            if (parameters == None or  parameters == "0.0.0.0" or parameters == 0 or parameters == "0" ):
                args = [ "del-controller", bridge ]
                parameters = "0.0.0.0"
            else:
                args = [ "set-controller", bridge, parameters ]
        elif command == "fail_mode":
            if (parameters == None):
                args = [ "del-fail-mode", bridge ]
            else:
                args = [ "set-fail-mode", bridge, parameters ]
        elif command == "ip":
            ovs_command = False
            if (parameters == None or parameters == "0.0.0.0" or parameters == "0"):
                args = [ "ifconfig", bridge, "0.0.0.0" ]
                parameters = "0.0.0.0"
            else:
                args = [ "ifconfig", bridge, parameters ]
                
        elif command == "dpid":
            # Ignore if none specified
            if parameters == None:
                args = [ "set", "Bridge", bridge, "other_config:datapath-id=0" ]
            else:
                args = [ "set", "Bridge", bridge, "other_config:datapath-id=" + parameters ]
        else:
            raise exception.CommandNotFound(command)
            
        if ovs_command:
            self.__exec_command(args)
        else:
            print "\n  $ "," ".join(args)
            subprocess.check_call(args)
        
        # Update database
        data_update = [ command, parameters ]
        entry = self.database.get_entry("VirtualBridges", bridge)
        entry["attributes"]["bridge_settings"][data_update[0]] = data_update[1]
    
    def add_port(self, bridge, port):
        """Add a port to the given bridge."""
        self.__exec_command(["add-port", bridge, port])
        entry = self.database.get_entry("VirtualBridges", bridge)
        entry["attributes"]["interfaces"].append(port)
    
    def delete_port(self, bridge, port):
        """Delete a port from the given bridge."""
        self.__exec_command(["del-port", bridge, port])
        entry = self.database.get_entry("VirtBridges", bridge)
        entry["attributes"]["interfaces"].remove(port)
    
    def modify_port(self, bridge, port, command, parameters=None):
        """Not currently allowed."""
        # Not allowing any port modifications at this time
        # May change at a later date
        raise exception.CommandNotFound("No port modifications to OVS allowed.")
    
    def show(self):
        """Returns the output of the show command as a byte string."""
        # Need to get output, which is not provided by __exec_command
        command = ["ovs-vsctl", "--db=unix:" + self.socket_file.name, "show"]
        print "\n  $ "," ".join(command)
        return subprocess.check_output(["ovs-vsctl", "--db=unix:" + self.socket_file.name, "show"])
        
        

