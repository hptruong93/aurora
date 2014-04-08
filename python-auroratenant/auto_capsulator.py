#!/usr/bin/python -tt
"""A module containing an HTTP server which will listen for incoming
capsulator tunnel configuration requests.  Upon receipt of a
configuration, it will set up a capsulator tunnel.

"""
import BaseHTTPServer
import copy
import json
import signal
import subprocess
import sys
import threading
import time
import traceback

# Install and import ifconfig
try:
    import ifconfig
except ImportError:
    def install(library):
        # Check if pip exists, if not, install it (easy install better exist)
        try:
            import pip
        except ImportError:
            try:
                subprocess.check_call(["easy_install", "pip"])
            except OSError:
                try:
                    subprocess.check_call(["apt-get", "install", "-y", "python-pip"])
                except subprocess.CalledProcessError:
                    raise PipInstallFailedError()
        
        try:
            subprocess.check_call(["pip", "install", library])
        except Exception:
            raise Exception("Installation of library %s failed" % library)

    install("python-ifconfig")
    import ifconfig

CAPSULATOR_BIN = "capsulator"
DEFAULT_BRINT_NAME = "brint"
try:
    BRINT_NAME = sys.argv[1]
except Exception as e:
    BRINT_NAME = DEFAULT_BRINT_NAME
SERVER_PORT = 5559
SERVER_ADDR = ('', SERVER_PORT)
BRIDGE_IP = "192.168.0.1/24"


class CapsulatorAgent(object):
    """Handles commands to do with setting up and tearing down 
    capsulator tunnel endpoints.

    If the machine running this script restarts, capsulator tunnels will
    not be rebuilt - the slices must be restarted using ap-slice-restart
    in order to notify this script of the presence of those slices 
    once again.

    """
    # Store process IDs in a dictionary by interface name.
    processes = {}
    def __init__(self, brint_name=BRINT_NAME, capsulator_bin=CAPSULATOR_BIN):
        """Performs checks to validate setting up a capsulator tunnel.

        :param str brint_name:
        :param str capsulator_bin:
        :raises: NoBridgeFoundException, NoCapsulatorBinException

        """
        # print "Constructing CapsulatorAgent %s" % repr(self)
        try:
            subprocess.check_call(["ifconfig", brint_name, "up"], 
                                  stdout=open("/dev/null", "w"))
        except subprocess.CalledProcessError:
            # bridge does not exist
            raise NoBridgeFoundException()
        else:
            if ifconfig.ifconfig(brint_name)["addr"] == "0.0.0.0":
                print "Setting %s ip to %s" % (brint_name, BRIDGE_IP)
                subprocess.check_call(
                    [
                        "ifconfig", 
                        brint_name, 
                        BRIDGE_IP
                    ], 
                    stdout=open("/dev/null", "w")
                )

        self.brint_name = brint_name
        try:
            subprocess.check_call([capsulator_bin],
                                  stdout=open("/dev/null", "w"))
        except subprocess.CalledProcessError:
            # capsulator not installed
            raise NoCapsulatorBinException()
        self.capsulator_bin = capsulator_bin

    @staticmethod
    def stop_all():
        """Stops all capsulator instances created by this script"""
        print "Stopping all processes"
        for interface in copy.deepcopy(CapsulatorAgent.processes):
            CapsulatorAgent.stop(interface)

    @staticmethod
    def stop(name):
        """Stops a single capsulator instance given by interface name.

        :param str name:
        :raises: NoProcessForInterfaceNameException

        """
        print "Stopping process for %s" % name
        try:
            pid = CapsulatorAgent.processes[name][0]
        except Exception as e:
            # Probably doesn't exist
            subprocess.call(["ip", "link", "del", name])
            raise NoProcessForInterfaceNameException(name=name)

        pid.terminate()
        pid.wait()
        subprocess.call(["ip","link","del",name])
        del CapsulatorAgent.processes[name]

    def create(self, config):
        """Sets up a capsulator tunnel using the information in config.
        A typical configuration looks like this::

            {  
                "attach_to": "eth0",
                "forward_to": "10.5.8.202",
                "command": "create",
                "name": "tun0",
                "tunnel_tag": "1"
            }

        :param dict config:
        :raises: InvalidConfigurationException, 
                 InterfaceNameAlreadyInUseException,
                 CannotBringInterfaceUpException,
                 CannotAddInterfaceToBridgeException

        """
        print "Creating %s" % config["name"]
        try:
            attach_to = config["attach_to"]
            forward_to = config["forward_to"]
            name = config["name"]
            tunnel_tag = config["tunnel_tag"]
        except Exception as e:
            raise InvalidConfigurationException()
        if (name in CapsulatorAgent.processes or 
            ifconfig.ifconfig(name).get("brdaddr") != "0.0.0.0"):
            raise InterfaceNameAlreadyInUseException(name=name)

        command = [self.capsulator_bin,"-t", attach_to, "-f", forward_to, 
                   "-vb", name + "#" + tunnel_tag]
        pid = subprocess.Popen(command)
        CapsulatorAgent.processes[name] = [pid]
        time.sleep(1)
        try:
            subprocess.check_call(["ifconfig", name, "up"])
        except subprocess.CalledProcessError:
            CapsulatorAgent.stop(name)
            raise CannotBringInterfaceUpException(name=name)
        try:
            subprocess.check_call(["brctl", "addif", self.brint_name, name])
        except subprocess.CalledProcessError:
            CapsulatorAgent.stop(name)
            raise CannotAddInterfaceToBridgeException(name=name,
                                                      bridge=self.brint_name)
        # CapsulatorAgent.processes[name].append(self.brint_name)

    def delete(self, config):
        """Stops a capsulator instance using information in config::

            {   
                "command": "delete",
                "name": "tun0"
            }

        :param dict config:

        """
        name = config["name"]
        print "Deleting %s" % name
        CapsulatorAgent.stop(name)

    def execute(self, command, config):
        """Entry point for processing capsulator commands.

        Possible commands are "create" and "delete".

        :param str command:
        :param dict config:
        :raises: InvalidCommandException

        """
        if command == "create":
            try:
                self.create(config)
            except AuroraTenantException as e:
                print e.message

            except Exception as e:
                traceback.print_exc(file=sys.stdout)
        elif command == "delete":
            try:
                self.delete(config)
            except AuroraTenantException as e:
                print e.message
        else:
            raise InvalidCommandException(command=command)


def exec_capsulator_command(command, config):
    """Interface for processing an auto_capsulator command"""
    try:
        CapsulatorAgent(brint_name=BRINT_NAME, 
                        capsulator_bin=CAPSULATOR_BIN).execute(command, config)
    except AuroraTenantException as e:
        print e.message
    except Exception as e:
        traceback.print_exc(file=sys.stdout)    

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version= "Aurora/0.2"

    # Not implemented
    def do_GET(self):
        """Not implemented"""
        self.send_response(400)
    

    def do_POST(self):
        """Use configuration data posted to set up a capsulator tunnel
        endpoint.

        ..warning::

            This does not check for validity of the sender,
            and can open up some big security issues.  No authentication is
            checked, meaning that anybody can set up a capsulator tunnel
            to the machine running this server!

        """
        # Parse the form data posted
        data_string = self.rfile.read(int(self.headers['Content-Length']))
        CFG = json.loads(data_string)
        print json.dumps(CFG, indent=4)

        command = CFG["command"]
        del CFG["command"]
        config = CFG

        # Process the command
        exec_capsulator_command(command, config)

        # Begin the response
        self.send_response(200)
        self.end_headers()

class AuroraTenantException(Exception):
    """Base class for exceptions in AuroraTenant.
    Inherit it and define info to use it.

    """
    
    # Based on OpenStack Nova exception setup
    # https://github.com/openstack/nova/blob/master/nova/exception.py
    message = "An unknown exception occurred."

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if not message:
            try:
                self.message = self.message % kwargs
            except Exception:
                self.message = AuroraException.message
                # message = self.message

        super(AuroraTenantException, self).__init__(self.message)

class NoBridgeFoundException(AuroraTenantException):
    message = "No valid bridge found"

class NoCapsulatorBinException(AuroraTenantException):
    message = "No capsulator binary found"

class InvalidConfigurationException(AuroraTenantException):
    message = "The given configuration appears invalid"

class InterfaceNameAlreadyInUseException(AuroraTenantException):
    message = "Interface name already in use: %(name)s"

class CannotBringInterfaceUpException(AuroraTenantException):
    message = "Could not bring interface %(name)s up"

class CannotAddInterfaceToBridgeException(AuroraTenantException):
    message = "Error adding interface %(name)s to bridge: %(bridge)s"

class CannotRemoveInterfaceFromBridgeException(AuroraTenantException):
    message = "Error removing interface %(name)s to bridge: %(bridge)s"

class NoProcessForInterfaceNameException(AuroraTenantException):
    message = "No process found for capsulator by name: %(name)s"

class InvalidCommandException(AuroraTenantException):
    message = "The command is invalid: %(command)s"

class PipInstallFailedError(AuroraTenantException):
    message = "Installation of python-pip failed"

def main():
    """Entry point for the auto_capsulator script"""
    HANDLER_CLS = RequestHandler
    server = BaseHTTPServer.HTTPServer(SERVER_ADDR, HANDLER_CLS)
    server_thread = threading.Thread(target=server.serve_forever)
    try:
        print "Starting server"
        server_thread.start()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)

    def signal_handler(signal, frame):
        print("Shutting down server")
        server.shutdown()

    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.pause()

if __name__ == "__main__":
    main()