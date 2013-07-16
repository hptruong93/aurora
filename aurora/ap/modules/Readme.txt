Notes on module structure

For modules compatible with the Virtual Interface class, the following structure
is required.

class Example:    

    def start(self, param1, param2, param3, param4.....):
        # Must return PID of process created
        return process.pid
        

    def stop(self, pid):
        # Kills the instance
        
    def status(self, pid):
        # Returns the status

    def kill_all(self):
        #Kills all known instances of the virtual interface.
            
There are some additional requirements not (explicitly) mentioned above.  These are:
-   The file name must match that of the flavour sent to the create() function
    in the Virtual Interfaces class.
-   The class name must be specified in the modules.json file.
-   The class must keep track of all interfaces/instances it creates.
-   Arguments sent to the create function in the Virtual Interfaces class
    in a dictionary must use key names that match the argument names in the start()
    function.

Please see either the veth or capsulator modules as an example.
