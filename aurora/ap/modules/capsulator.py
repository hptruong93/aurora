# Capsulator class
# Configures and runs the capsulator program developed by Stanford (v 0.01b)
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import subprocess, copy, time
class Capsulator:    

    # Number of times to retry starting capsulator if it fails
    retry_attempts = 2
    
    def __init__(self):
        # Keep track of all created instances
        # Inside the dictionary is a list
        # Format: [ process instance, interface name ]
        self.process_list = {}

    def start(self, attach_to, forward_to, name, tunnel_tag, is_virtual=True):
        """Starts an instance of capsulator.  Returns PID.
        
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
       
        # Launch process
        process = subprocess.Popen(command)
        
        # Bring interface up; this will throw an exception if it fails
        # We want an exception if it fails, but it might fail if capsulator
        # is not ready.  In that case, we want to retry before giving up
        # and sending the exception along.
        interface_command = [ "ifconfig", name, "up" ]
        
        attempts = 0
        while attempts < self.retry_attempts:
            try:
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
                    subprocess.call(["ip", "link", "del", name])
                    raise
                
                # Sleep for 1 second; should be enough
                time.sleep(1)
        
        self.process_list[process.pid] = [ process , name ]
        
        return process.pid
        

    def stop(self, pid):
        """Stops an instance of capsulator with this PID."""
        # Get process, name, remove entry by popping
        process = self.process_list[pid][0]
        name = self.process_list.pop(pid)[1]
        process.terminate()
        # Need .wait(), otherwise process hangs around as defunct.
        process.wait()
        
        # Delete old interface
        # Will not raise exception if it fails; this is OK
        subprocess.call(["ip", "link", "del", name])
        
        
    def status(self, pid):
        """Returns whether or not the given instance is running."""
        # None = still running.  Any return code = finished
        return self.process_list.get(pid)[0].poll() == None


    def kill_all(self):
        """Stops all known instances of capsulator."""
        for key in copy.deepcopy(self.process_list):
            self.stop(key)
