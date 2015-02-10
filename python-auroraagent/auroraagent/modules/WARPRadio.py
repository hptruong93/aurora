# SAVI McGill: HP Truong, Al Kenny

import subprocess, sys
import json
import zmq, ZeroMQThread
import socket
import time
import config
import inspect


def ln(stringhere = 'was here', number_of_dash = 40):
    print("%s:%s %s> %s"% (__file__, inspect.currentframe().f_back.f_lineno, '-'*number_of_dash, stringhere))

class WARPRadio:

    def __init__(self, database, sending = config.CONFIG["zeromq"]["sending"], receiving  = config.CONFIG["zeromq"]["receiving"], macaddr = "40:d8:55:04:22:84"):
        self.sending_socket_number = str(sending)
        self.receiving_socket_number = str(receiving)
        self.database = database
        self.WARP_mac = macaddr

        self.start()        

    def __del__(self):

        # free up the sockets when we are done

        port_usage = subprocess.check_output(["netstat", "-ap", "|", "grep", ":%s" % self.sending_socket_number])

        if len(port_usage) is not 0:
            self.sending_socket.close()
            subprocess.check_call(["fuser", "-k", self.sending_socket_number + "/tcp"])

        port_usage = subprocess.check_output(["netstat", "-ap", "|", "grep", ":%s" % self.receiving_socket_number])

        if len(port_usage) is not 0:
            self.receiving_socket.close()
            subprocess.check_call(["fuser", "-k", self.receiving_socket_number + "/tcp"])

    def start(self):

        self.sleep_time = 0.2
        self.action_timeout = 5
        self.continue_to_receive = True

        # we need to perform some actions asynchronously (delete slice) while preventing any sort of issues from arising in the meantime
        # format: {"<name of command>": {"success": <True/False>, "error": "<returned error>"}}
        self.pending_action = {}

        self.ovs_information = {} 

        context = zmq.Context()

        self.subscription = str(config.CONFIG["zeromq"]["subscription"])
        self.subscription_length = len(self.subscription)


        # this will be the socket over which information is sent to relay agent server
        # thus it should be a zmq client with PUB
        self.sending_socket = context.socket(zmq.PUB)
        self.sending_socket.bind("tcp://*:%s" % self.sending_socket_number)


        # Start the receiver thread which will handle replies from relay agent and direct them to the function
        # which parses the result of the actions sent to relay agent
        self.receiving_socket = context.socket(zmq.SUB)
        self.receiving_socket.connect("tcp://localhost:%s" % self.receiving_socket_number)
        self.receiving_socket.setsockopt(zmq.SUBSCRIBE, self.subscription) 
        self.test_thread = ZeroMQThread.ZeroMQThread(self.receive_WARP_info)
        self.test_thread.start() 

        # subscriber likely to miss first message
        self.sending_socket.send("%s test" %self.subscription)

        # self.start_sender()
        # self.start_receiver_thread()
               

        

    def shutdown(self):
        # The other end of relay agent will reply with a confirmation of the shutdown notification so that the
        # call to self.receiving_socket.recv() stops blocking and the thread can die
        shutdown_json = json.dumps({"command": "shutdown"})
        self.sending_socket.send("%s %s" % (self.subscription, shutdown_json))

    def start_receiver_thread(self):
        pass

    def start_sender(self):
        pass

    def add_pending_action(self, action_title, command):
        # may have to add in an action ID in the future to distinguish between multiple pending actions of the same type

        command = json.dumps(command)

        # add the success, error and start time fields for later referencing
        self.pending_action[action_title] = {"success": False, "error": "", "start_time": int(round(time.time() * 1000))}
        while action_title not in self.pending_action: 
            time.sleep(self.sleep_time)    #wait for the action to appear in the pending_action list

        # once we know that the action has been added to the list, we can send the info to relayagent
        self.sending_socket.send("%s %s" %(self.subscription, command))

        waiting_action = self.pending_action[action_title]

        # we want to wait for the action to either complete or to come back as having not completed due to an error
        while (waiting_action["success"] != True) and (waiting_action["error"] == "") and \
        ((int(round(time.time() * 1000)) - waiting_action["start_time"]) < self.action_timeout*1000):
            time.sleep(self.sleep_time)

        # ln("time: %s\nstart_time: %s\ndifference: %s\ntimeout value: %s" % (int(round(time.time() * 1000)), waiting_action["start_time"], 
        #     int(round(time.time() * 1000))- waiting_action["start_time"], self.action_timeout*1000))

        if waiting_action["error"] == "": # we have not RECEIVED an error, it may be that the error was a timeout on our end
            if waiting_action["success"]:          
                result = {"success": True, "error": ""}
            else:
                # no error and unsuccessful means a timeout
                result = {"success": False, "error": "timeout"}
        else:
            result = {"success": False, "error": waiting_action["error"]}    # document the error

        del self.pending_action[action_title] 
        # ln("deleting action title: %s" % action_title)

        return result

    def wifi_up(self, radio):

        # finding the number of radios that are currently up
        interfaces = subprocess.Popen("uci show | grep =wifi-iface", shell = True, stdout = subprocess.PIPE)
        radio_numbers = []
        for line in interfaces.stdout:
            radio_numbers.append(line[21])

        radio_info = {}

        option_types = ["type","channel","hwmode","macaddr","disabled","htmode","ht_capab"]

        for num in radio_numbers:

            radio_name = ["radio",str(num)]

            section = "".join(radio_name)
            radio_info[section] = {}

            for option in option_types:
                # print radio_info

                attribute = "wireless." + section + "." + option
                # print "attribute = " + attribute

                command = ["uci","get",attribute]
                output = subprocess.Popen(command, shell = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                value  = output.stdout.readline()

                value  = value.rstrip()
                # print "attribute value for " + attribute + " = " + value

                if (output.stderr.readline() != "uci: Entry not found\n"):
                    if (" " in value):
                        # print "value before = " + value
                        value = value.split()

                    radio_info[section][option] = value
                    
        radio_info = {"command":"wifi up", "changes": radio_info}
        radio_info_string = json.dumps(radio_info)
        self.sending_socket.send("%s %s" %(self.subscription,radio_info_string))
        
    def wifi_down(self, radio = None):

        if radio is None:    
            wifi_down_string  = json.dumps({"command":"wifi down", "changes": "all"})            
            # print "\n  $ wifi down all"            
            #subprocess.call(["wifi", "down", str(radio)])
        else:    
            wifi_down_string  = json.dumps({"command": "wifi down", "changes":str(radio)})
            # print "\n  $ wifi down " + str(radio)
            #subprocess.call(["wifi", "down", str(radio)])

        self.sending_socket.send("%s %s" %(self.subscription,wifi_down_string))
            
    def wifi_detect(self):

        detect_dummy = {"command":"wifi_detect", "changes": "dummy"}
        sending = json.dumps(detect_dummy)

        self.sending_socket.send("%s %s" %(self.subscription, sending))
        
    
    def wifi_detect_receive(self, WARP_wifi):
        # expecting a json file of the form

        # config wifi-device  radio0
        #     option type     mac80211
        #     option channel  11
        #     option hwmode   11ng
        #     option macaddr  00:21:5d:22:97:8c
        #     option htmode   HT20
        #     list ht_capab   GF
        #     list ht_capab   SHORT-GI-20
        #     list ht_capab   SHORT-GI-40
        #     # REMOVE THIS LINE TO ENABLE WIFI:
        #     option disabled 1

        self.detect = WARP_wifi

        # for radio in WARP_wifi:
        #     print "config wifi-device  " + str(radio)
        #     for option in radio:
        #         if (option is "disabled") and (radio[option] is "1"):
        #             print "# REMOVE THIS LINE TO ENABLE WIFI:"
        #             print "\toption disabled\t 1"
        #         elif isinstance(radio[option], list):
        #             for item in radio[option]:
        #                 print "\toption " + option + "\t" + str(item) 
        #         else:
        #             print "\toption " + option + "\t" + str(radio[option]) 

    """ The folllowing 6 functions perform every possible altering action for a slice """

    def _bulk_radio_set_command(self, radio, command_dict):
        prtcmd = {"radio": radio, "command": "_bulk_radio_set_command", "changes": command_dict}
        result = self.add_pending_action("_bulk_radio_set_command", prtcmd)

        return result

    def _create_new_section(self, section_type, radio, bssid = None):
        prtcmd = {"command": "_create_new_section", "radio":radio, "changes" : {"macaddr": bssid, "section" :section_type}}
        result = self.add_pending_action("_create_new_section", prtcmd)

        return result

    def _delete_section_name(self, section, radio, bssid = None):
        prtcmd = {"command": "_delete_section_name", "radio": radio, "changes": {"section": str(section), "macaddr": bssid}}
        result = self.add_pending_action("_delete_section_name", prtcmd)           
        
        return result

    def _delete_bss_index(self, bss_num, bssid = None):
        prtcmd = {"command": "_delete_bss_index", "radio":radio, "changes" : {"index":str(bss_num), "macaddr": bssid}}
        result = self.add_pending_action("_delete_bss_index", prtcmd)

        return result

    def _delete_radio(self, radio, section, bssid = None):
        prtcmd = {"command": "_delete_radio", "radio":radio, "changes" : {"macaddr": bssid, "section": str(section)}}
        result = self.add_pending_action("_delete_radio", prtcmd)

        return result

    def _add_wireless_section(self, section, bssid = None):
        prtcmd = {"command": "_add_wireless_section", "radio":radio, "changes" : {"section":str(section), "macaddr": bssid}}
        result = self.add_pending_action("_add_wireless_section", prtcmd)

        return result

    ##################################

    def action_result_reception(self, action_title, command_json):
        # the reply for each of the 6 actions above will filter through this function

        pending_action = self.pending_action[str(action_title)]
        if command_json["changes"]["success"]:            
            pending_action["success"] = True
        else:
            pending_action["error"] = command_json["changes"]["error"]

    
    def receive_WARP_info(self):
        # run as a server in thread
        # will be used in the secondary thread to listen for radio information from WARP via relayagent

        while self.continue_to_receive: 
            # ln("here's where the error is likely occuring")
            #get the message
            message = self.receiving_socket.recv()

            #sometimes the test send might be seen at the beginning of sub/pub comms
            #we want to ignore it
            test = "%s test" % self.subscription

            ln("Receiving: %s" % message)
                
            if message != test:
                # get the actual response by stripping the subscription number from the received string as well as
                # its accompanying space (inherent to PUB/SUB comms) and the trailing null terminator from cpp
                message = message[self.subscription_length+1:-1]

                WARP_response = json.loads(message)

                if WARP_response["command"] != "wifi down":
                    # we don't care about wifi down
                    if WARP_response["command"] == "wifi_detect":
                        self.wifi_detect_receive(WARP_response["configuration"])
                    elif WARP_response["command"][0] == "_":
                        # any command beginning with an underscore is related to the setup/change process,
                        # thus we route the info returned from the WARP board to the receive action_result_reception function
                        if WARP_response["command"] == "_ovs_socket_path":
                            self.ovs_information = WARP_response["changes"]
                        else:    
                            try:                            
                                command_json  = {"changes": WARP_response["changes"], "radio": WARP_response["radio"]}
                            except:
                                command_json  = {"changes": WARP_response["changes"]}

                            self.action_result_reception(WARP_response["command"],command_json)
                    elif WARP_response["command"] == "shutdown":
                        # we've received a reply from the cpp relay agent which is serving only to stop the recv function from blocking
                        # the shutdown
                        self.continue_to_receive = False

