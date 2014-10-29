# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import subprocess
import psutil
import copy
class Veth:    
    """The veth class configures and runs the veth program,
    written by Nestor Pena.  The original website no longer exists;
    the only website still running appears to be
    http://www.geocities.ws/nestorjpg/veth/index.html"""
    def __init__(self):
        # Keep track of all created instances
        self.process_list = {}

    def start(self, attach_to, name, mac=0):
        """Starts an instance of vethd. An exception will be thrown
        if the program fails to start.
        
        name = Name you want in the VIRTUAL device, for example: veth0
        attach_to = Name of the REAL device, for example: eth0, eth1
        mac = MAC address desired, like this: 00:11:22:33:44:55
        
        If mac is not specified, it is generated by the kernel."""
        if mac != 0 :
            command = ["vethd","-e", attach_to, "-v", name,"-m", mac]
        else:
            command = ["vethd","-e", attach_to,"-v", name]

        # TODO: see if subprocess can be replaced with psutil
        
        # Launch program.  Will raise exception if there is an issue.
        print "\n  $ "," ".join(command)
        subprocess.check_call(command)
        
        # Bring interface up
        interface_command = [ "ifconfig", name, "up" ]
        
        print "\n  $ "," ".join(interface_command)
        subprocess.check_call(interface_command)
        
        process = None
        # Since veth forks, we need to find the PID
        for i in psutil.process_iter():
            if i.cmdline == command:
                process = i
                self.process_list[name] = process
        

    def stop(self, name):
        """Stops the process with given name, assuming it is a vethd process."""
        
        process = self.process_list[name]
        process.terminate()
        # Need .wait(), otherwise process hangs around as defunct.
        process.wait()
        
        # Delete entry now that the process has truly been deleted
        del self.process_list[name]

    def status(self,name ):
        """Returns whether or not the given instance is running."""
        return self.process_list.get(name).is_running()
    
    def kill_all(self):
        """Kills all known vethd processes."""
        for key in copy.deepcopy(self.process_list):
            self.stop(key)
            
