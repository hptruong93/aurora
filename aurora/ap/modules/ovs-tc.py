# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith
import subprocess
import psutil
import copy
class OvsTC:    
    """The ovs-tc class sets up ovs queues on bridge interfaces"""
    def __init__(self):
        # Keep track of all created instances
        self.process_list = {}

    def start(self, rate_up = None, rate_down = None, if_up = None, if_down = None, ovs_db_sock = None, name = None):
        """Sets up queues and using ovs-vsctl to limit rates to specified limits."""

        if ovs_db_sock is None:
            raise Exception("TC Error: no ovs sock specified")

        # Check that for supplied rates, if is specified
        if (rate_up and not if_up) or (rate_down and not if_down):
            # Need interface
            raise Exception("TC Error: No interface on which to apply QOS")

        qos_list = []
        if rate_up:
            qos_list.append((rate_up, if_up))
        if rate_down:
            qos_list.append((rate_down, if_down))
        for qos_rule in qos_list:
            command = ["ovs-vsctl", "--db=unix:%s" % ovs_db_sock,"clear", "Port", qos_rule[1], "qos"]
            print "\n  $ "," ".join(command)
            try:
                subprocess.check_call(command)
            except:
                pass

            command = [
                "ovs-vsctl", "--db=unix:%s" % ovs_db_sock, 
                   "--", "set", "port", qos_rule[1], "qos=@rate_limit_qos", 
                   "--", "--id=@rate_limit_qos", "create", "qos", "type=linux-htb",
                         "other-config:max-rate=%s" % qos_rule[0], "queues:0=@q0", 
                   "--", "--id=@q0", "create", "queue", "other-config:max-rate=%s" % qos_rule[0]
                ]
            print "\n  $ "," ".join(command)
            try:
                subprocess.check_call(command)
            except:
                pass

            # Add rules to flow table 
            #command = [
            #    "ovs-ofctl", "--db=unix:%s" % ovs_db_sock, 
            #       "--", "set", "port", qos_rule[1], "qos=@rate_limit_qos", 
            #       "--", "--id=@rate_limit_qos", "create", "qos", "type=linux-htb",
            #             "other-config:max-rate=%s" % qos_rule[0], "queues:0=@q0", 
            #       "--", "--id=@q0", "create", "queue", "other-config:max-rate=%s" % qos_rule[0]
            #    ]
            #print "\n  $ "," ".join(command)
            #try:
            #    subprocess.check_call(command)
            #except:
            #    pass

    def stop(self, if_up = None, if_down = None, ovs_db_sock = None):
        if if_up:
            qos_list.append(if_up)
        if if_down:
            qos_list.append(if_down)
        for qos_rule in qos_list:
            command = ["ovs-vsctl", "--db=unix:%s" % ovs_db_sock,"clear", "Port", qos_rule, "qos"]
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
            
