# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import subprocess, copy, time
class Capsulator:    
    """The Capsulator class provides an interface to interact with the
    capsulator program developed by Stanford (v. 0.01b) and modified
    by the BCRL at McGill University to implement IP-based incoming 
    tunnel data filtering."""
    # Number of times to retry starting capsulator if it fails
    retry_attempts = 2
    
    def __init__(self):
        # Keep track of all created instances
        # Inside the dictionary is a list
        # Format: [ capsulator interface name, process instance ]
        self.process_list = {}

    def start(self, attach_to, forward_to, name, tunnel_tag, is_virtual=True):
        """Starts an instance of capsulator.  Please note that incorrect configuration
        can cause the program to fail to start, and an exception may NOT be 
        generated.  The status can be checked with the status command.
        
        attach_to = names the interface which is the tunnel endpoint
        forward_to = the IP the tunnel should forward frames to
        name = specifies a border interface
        tag = the tag of the border interface
        is_virtual = whether or not to create a virtual interface for
                  border_interface (i.e. a tap).  In this case, 
                  border_interface should not be a real 
                  interface, as it will be created automatically."""
        if (is_virtual == True or is_virtual == None) :
            command = ["capsulator","-t", attach_to, "-f", forward_to, "-vb", name + "#" + tunnel_tag]
        else:
            command = ["capsulator","-t", attach_to, "-f", forward_to, "-b", name + "#" + tunnel_tag]
       
        # Make sure capsulator with that name is not already running
        if name in self.process_list:
            raise exception.NameAlreadyInUse("Capsulator already running with " + name)
       
        # Launch process
        print "\n  $ "," ".join(command)
        process = subprocess.Popen(command)
        
        # Bring interface up; this will throw an exception if it fails
        # We want an exception if it fails, but it might fail if capsulator
        # is not ready.  In that case, we want to retry before giving up
        # and sending the exception along.
        interface_command = [ "ifconfig", name, "up" ]
        
        attempts = 0
        while attempts < self.retry_attempts:
            try:
                print "\n  $ "," ".join(interface_command)
                subprocess.check_call(interface_command)
                # Successful, break out of loop
                break
            except subprocess.CalledProcessError, e:
                attempts += 1
                # If too many times, give up and raise exception
                # Attempt to delete capsulator
                if attempts == self.retry_attempts:
                    process.terminate()
                    process.wait()
                    command = ["ip", "link", "del", name]
                    
                    print "\n  $ "," ".join(command)
                    subprocess.call(["ip", "link", "del", name])
                    raise
                
                # Sleep for 1 second; should be enough
                # Unfortunately, there is no known better way
                time.sleep(1)
        
        
        self.process_list[name] = process
        
        return process.pid
        

    def stop(self, name):
        """Stops an instance of capsulator with this name."""
        # Get process, kill
        process = self.process_list[name]
        process.terminate()
        # Need .wait(), otherwise process hangs around as defunct.
        process.wait()
        
        # Delete old interface
        # Will not raise exception if it fails; this is OK
        command = ["ip", "link", "del", name]
        print "\n  $ "," ".join(command)
        subprocess.call(command)
        
        # Remove entry
        del self.process_list[name]
        
        
    def status(self, name):
        """Returns whether or not the given instance is running."""
        # None = still running.  Any return code = finished
        return self.process_list[name].poll() == None


    def kill_all(self):
        """Stops all known instances of capsulator."""
        for key in copy.deepcopy(self.process_list):
            self.stop(key)
