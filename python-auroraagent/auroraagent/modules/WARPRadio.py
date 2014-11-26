#!/usr/bin/python

import subprocess, json, zmq, sys, ZeroMQThread, socket, time, config


def ln(stringhere):
    print "%s %s-------------------------------------------> %s"% (inspect.currentframe().f_back.f_lineno,inspect.getfile(inspect.currentframe()), stringhere)

class WARPRadio:

    def __init__(self, database, sending = config.CONFIG["zeromq"]["sending"], receiving  = config.CONFIG["zeromq"]["receiving"], macaddr = "40:d8:55:04:22:84"):
        self.sending_socket_number = str(sending)
        self.receiving_socket_number = str(receiving)
        self.database = database
        self.detect = ''
        self.sleep_time = 0.5
        self.action_timeout = 5

        context = zmq.Context()

        # note that the publisher is associated with a port through the use of the
        # bind() statement while the subscriber uses connect(). Additionally,
        # it appears that tcp://* is used for publisher while tcp://localhost
        # is used for subscriber

        self.receiving_socket = context.socket(zmq.SUB)
        self.receiving_socket.connect("tcp://localhost:%s" % self.receiving_socket_number)
        self.subscription = str(config.CONFIG["zeromq"]["subscription"])
        self.subscription_length = len(self.subscription)
        self.receiving_socket.setsockopt(zmq.SUBSCRIBE, self.subscription)
        self.test_thread = ZeroMQThread.ZeroMQThread(self.receive_WARP_info)
        self.test_thread.start()
        self.WARP_mac = macaddr
        self.pending_action = {}    # we need to perform some actions asynchronously (delete slice) while preventing any sort of issues from arising in the meantime
                                    # format: {"<name of command>": {"success": <True/False>, "error": "<returned error>"}}

        # this will be the socket over which information is sent to Alan's server
        # thus it should be a zmq client with REQ
        context = zmq.Context()
        self.sending_socket = context.socket(zmq.PUB)
        self.sending_socket.bind("tcp://*:%s" % self.sending_socket_number)

        # subscriber likely to miss first message
        self.sending_socket.send("%s test" %self.subscription)




    def __del__(self):

        # free up the sockets when we are done

        port_usage = subprocess.check_output(["netstat", "-ap", "|", "grep", ":%s" % sending_socket_number])

        if len(port_usage) is not 0:
            self.sending_socket.close()
            subprocess.check_call(["fuser", "-k", self.sending_socket_number + "/tcp"])


        port_usage = subprocess.check_output(["netstat", "-ap", "|", "grep", ":%s" % receiving_socket_number])

        if len(port_usage) is not 0:
            self.receiving_socket.close()
            subprocess.check_call(["fuser", "-k", self.receiving_socket_number + "/tcp"])

    def add_pending_action(action_title):
        # may have to add in an action ID in the future to distinguish between multiple pending actions of the same type
        self.pending_action[action_title] = {"success": False, "error": "", "start_time": int(round(time.time() * 1000))}

    def clear_pending_action(action_title):
        del self.pending_action[action_title]

    def wait_on_pending_action(action_title, timeout):
        while action_title not in self.radio.pending_action: 
            time.sleep(self.sleep_time)    #wait for the action to appear in the pending_action list                
        waiting_action = self.pending_action[action_title]
        while not waiting_action["success"] and waiting_action["error"] == "" and (int(round(time.time() * 1000)) - waiting_action["start_time"]) < int(timeout):
            time.sleep(self.sleep_time)   # we want to wait for the action to either complete or to come back as having not completed due to an error    

    def wifi_up(self, radio):

        interfaces = subprocess.Popen("uci show | grep =wifi-iface", shell = True, stdout = subprocess.PIPE)

        radio_numbers = []

        for line in interfaces.stdout:
            radio_numbers.append(line[21])

        radio_info = {}

        option_types = ["type","channel","hwmode","macaddr","disabled","htmode","ht_capab"]

        for i in radio_numbers:

            radio_name = ["radio",str(i)]

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

    def _bulk_radio_set_command(self, radio, command_dict):
        prtcmd = {"radio": radio, "command": "_bulk_radio_set_command", "changes": command_dict}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    # def _radio_set_command(self, radio, command, value):
    #     # prtcmd = ["_radio_set_command","uci","set","wireless.radio" + str(radio_num) + "." + str(command) + "=" +str(value)]
    #     prtcmd = {"radio": radio, "command": "_radio_set_command", "changes" : {"wireless":"wireless.radio%s.%s=%s" % (name.lstrip("radio"),str(command),str(value))}}
    #     prtcmd = json.dumps(prtcmd)
    #     self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    # def _generic_set_command(self, section, command, value):
    #     # prtcmd = ["_generic_set_command","uci","set", "wireless." + str(section) + "." + str(command) + "=" +str(value)]
    #     prtcmd = {"command": "_generic_set_command", "changes" : {"wireless":"wireless.%s.%s=%s" % (str(section),str(command),str(value))}}
    #     prtcmd = json.dumps(prtcmd)
    #     self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _create_new_section(self, section_type, radio, bssid = None):
        prtcmd = {"command": "_create_new_section","changes" : {"radio":radio, "macaddr": bssid, "section" :section_type}}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _delete_section_name(self, section, bssid = None):
        # add_pending_action)("_delete_section_name")
        prtcmd = {"command": "_delete_section_name","changes" : {"section": str(section), "macaddr": bssid}}
        prtcmd = json.dumps(prtcmd)
        self.add_pending_action("_delete_section_name")
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))
        self.wait_on_pending_action("_delete_section_name")     
        action_result = self.pending_action["_delete_section_name"]   
        if action_result["success"]:          
            result = {"success": True, "error": ""}
        else if not action_result["success"]:
            if action_result["error"] == "":
                # no error and unsuccessful means a timeout
                result = {"success": False, "error": "timeout"}
            else:
                result = {"success": False, "error": action_result["error"]}

        self.clear_pending_action["_delete_section_name"]
        return result



    def _delete_bss_index(self, bss_num, bssid = None):
        prtcmd = {"command": "_delete_bss_index","changes" : {"index":str(bss_num), "macaddr": bssid}}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _delete_radio(self, radio, section, bssid = None):
        prtcmd = {"command": "_delete_radio", "changes" : {"radio":radio, "macaddr": bssid, "section": str(section)}}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _add_wireless_section(self, section, bssid = None):
        prtcmd = {"command": "_add_wireless_section", "changes" : {"section":str(section), "macaddr": bssid}}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))





    # the receive functions paired with the above sending functions

    def _bulk_radio_set_command_receive(self, command_json):
        radio_entry = self.database.hw_get_radio_entry(command_json["radio"])
        for item in command_json["changes"]:
            if command_json["changes"][item] != radio_entry[item]:
                radio_entry[item] = command_json["changes"][item]

                ln("call function in Receive.py to send info to manager")

    # def _radio_set_command_receive(self, command_json):
    #     radio_entry = self.database.hw_get_radio_entry(command_json["radio"])
    #     # print "\n  $ "," ".join(prtcmd)
    #     #subprocess.check_call(["uci","set",str(prtcmd[3])])    

    # def _generic_set_command_receive(self, command_json):
    #     radio_entry = self.database.hw_get_radio_entry(command_json["radio"])
    #     # print "\n  $ "," ".join(prtcmd)
    #     #subprocess.check_call(["uci","set", str(prtcmd[3])])

    def _create_new_section_receive(self, command_json):
        pass 

    def _delete_section_name_receive(self, command_json):
        if command_json["success"]:            
            ln("we need to coordinate on a key/item in received json corresponding success/failure")
            self.pending_action["_delete_section_name"]["success"] = True
        else:
            self.pending_action["_delete_section_name"]["success"] = False
            self.pending_action["_delete_section_name"]["error"] = "returned_error"
            ln("we need to change\"returned_error\" to the actual error received from WARP")

    def _delete_bss_index_receive(self, command_json):
        pass

    def _delete_radio_receive(self, command_json):
        pass  

    def _add_wireless_section_receive(self, command_json):
        pass


    
    def receive_WARP_info(self):
        # run as a server in thread
        # will be used in the secondary thread to listen for radio information from WARP

        while True: 
            #get the message
            message = self.receiving_socket.recv()

            #sometimes the test send might be seen at the beginning of sub/pub comms
            #we want to ignore it
            test = self.subscription + " test"

            if message != test:
                # get the actual response by stripping the subscription number from the received string
                WARP_response = json.loads(message[self.subscription_length+1:])

                if (WARP_response["command"] != "wifi down"):
                    # we don't care about wifi down
                    if WARP_response["command"] == "wifi_detect":
                        self.wifi_detect_receive(WARP_response["configuration"])
                    elif WARP_response["command"][0] == "_":
                        # any command beginning with an underscore is related to the setup/change process
                        # thus we route the info returned from the WARP board to the receive function
                        # paired to the function that sent it

                        try:                            
                            command_json  = {"changes": WARP_response["changes"], "radio": WARP_response["radio"]}
                        except:
                            command_json  = {"changes": WARP_response["changes"]}
                        getattr(self, "%s_receive" % WARP_response["command"])(command_json)
