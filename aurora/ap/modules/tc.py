# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import subprocess
import psutil
import copy
class Tc:    
    """The veth class configures and runs the veth program,
    written by Nestor Pena.  The original website no longer exists;
    the only website still running appears to be
    http://www.geocities.ws/nestorjpg/veth/index.html"""
    def __init__(self):
        # Keep track of all created instances
        self.process_list = {}

    def start(self, rate_up = None, rate_down = None, if_up = None, if_down = None):
        """Sets up qdiscs and classes using TC to limit rates to specified limits."""

        # Check that for supplied rates, if is specified
        if (rate_up not None and not if_up) or (rate_down not None and not if_down):
            # Need interface
            raise Exception("TC Error: No interface on which to apply QOS")

        qos_list = []
        if rate_up not None:
            qos_list.append((rate_up, if_up))
        if rate_down not None:
            qos_list.append((rate_down, if_down))
        for qos_rule in qos_list:
            command = ["tc", "qdisc", "del", "dev", qos_rule[1], "root"]
            print "\n  $ "," ".join(command)
            subprocess.check_call(command)
            command = ["tc", "qdisc", "add", "dev", qos_rule[1], "root", 
                       "handle", "1:", "htb"]
            print "\n  $ "," ".join(command)
            subprocess.check_call(command)
            command = ["tc", "class", "add", "dev", qos_rule[1], "parent", "1:",
                       "classid", "1:1", "htb", "rate", qos_rule[0]]
            print "\n  $ "," ".join(command)
            subprocess.check_call(command)
            command = ["tc", "filter", "add", "dev", qos_rule[1], "parent", "1:0",
                       "protocol", "ip", "prio", "1", "u32","match",
                       "ip", "dst", "0.0.0.0/0", "flowid", "1:1"]
            print "\n  $ "," ".join(command)
            subprocess.check_call(command)
            command = ["tc", "qdisc", "add", "dev", qos_rule[1], "parent", "1:1", "handle", "10:", "sfq", "perturb", "10"]
            print "\n  $ "," ".join(command)
            subprocess.check_call(command)

    def stop(self, if_up = None, if_down = None):
        if rate_up not None:
            qos_list.append((rate_up, if_up))
        if rate_down not None:
            qos_list.append((rate_down, if_down))
        for qos_rule in qos_list:
            command = ["tc", "qdisc", "del", "dev", qos_rule[1], "root"]
            print "\n  $ "," ".join(command)
            try:
                subprocess.check_call(command)
            except Exception:
                # Virtual interface was likely already deleted
                pass
        

    def status(self,name ):
        """Returns whether or not the given instance is running."""
        return self.process_list.get(name).is_running()
    
    def kill_all(self):
        """Kills all known vethd processes."""
        for key in copy.deepcopy(self.process_list):
            self.stop(key)
            
