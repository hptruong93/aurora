#!/usr/bin/python

import subprocess
import json
import zmq
import sys
import ZeroMQThread
import socket
import time
import config

class WARPRadio:

    def __init__(self, sending = config.CONFIG["zeromq"]["sending"], receiving  = config.CONFIG["zeromq"]["receiving"], mac_addr = "40:d8:55:04:22:84"):
        self.sending_socket_number = str(sending)
        self.receiving_socket_number = str(receiving)

        context = zmq.Context()

        self.detect = 0

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

        self.WARP_mac = mac_addr

        # this will be the socket over which information is sent to Alan's server
        # thus it should be a zmq client with REQ
        context = zmq.Context()
        self.sending_socket = context.socket(zmq.PUB)
        self.sending_socket.bind("tcp://*:%s" % self.sending_socket_number)

        # subscriber likely to miss first message
        self.sending_socket.send("%s test" %self.subscription)

        time.sleep(1)




    def __del__(self):

        # free up the sockets when we are done

        port_usage = subprocess.Popen("sudo netstat -ap | grep :" + sending_socket_number, shell = True, stdout= subprocess.PIPE)

        if len(port_usage.stdout.readline()) is not 0:
                self.sending_socket.close()
                subprocess.call(["fuser", "-k", self.sending_socket_number + "/tcp"])


        port_usage = subprocess.Popen("sudo netstat -ap | grep :" + receiving_socket_number, shell = True, stdout= subprocess.PIPE)

        if len(port_usage.stdout.readline()) is not 0:
                self.receiving_socket.close()
                subprocess.call(["fuser", "-k", self.receiving_socket_number + "/tcp"])


    def wifi_up(self, radio):
    
        print "radio = " + radio
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

        print self.detect

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

    def _bulk_radio_set_command(self, command_dict):
        prtcmd = {"command": "_bulk_radio_set_command", "changes": command_dict}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _radio_set_command(self, radio_num, command, value):
        # prtcmd = ["_radio_set_command","uci","set","wireless.radio" + str(radio_num) + "." + str(command) + "=" +str(value)]
        prtcmd = {"command": "_radio_set_command", "changes" : "wireless.radio%s.%s=%s" % (str(radio_num),str(command),str(value))}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _generic_set_command(self, section, command, value):
        # prtcmd = ["_generic_set_command","uci","set", "wireless." + str(section) + "." + str(command) + "=" +str(value)]
        prtcmd = {"command": "_generic_set_command", "changes" : "wireless.%s.%s=%s" % (str(section),str(command),str(value))}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _create_new_section(self, section_type, name):
        # prtcmd = ["_create_new_section","uci","set", "wireless." + str(name) + "=" +str(section_type)]
        prtcmd = {"command": "_create_new_section","changes" : "wireless.%s=%s" % (str(name),str(section_type))}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _uci_delete_section_name(self, section):
        # prtcmd = ["_uci_delete_section_name","uci","delete","wireless." + str(section)]
        prtcmd = {"command": "_uci_delete_section_name","changes" : "wireless.%s" % str(section)}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _uci_delete_bss_index(self, bss_num):
        # prtcmd = ["_uci_delete_bss_index","uci","delete","wireless.@wifi-iface[" + str(bss_num) + "]"]
        prtcmd = {"command": "_uci_delete_bss_index","changes" : "wireless.@wifi-iface[%s]" % str(bss_num)}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _uci_delete_radio(self, radio_num, section):
        # prtcmd = ["_uci_delete_radio","uci","delete","wireless.radio" + str(radio_num) + "." + str(section)]
        prtcmd = {"command": "_uci_delete_radio", "changes" : "wireless.radio%s.%s" (str(radio_num), str(section))}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))

    def _uci_add_wireless_section(self, section):
        # prtcmd = ["_uci_add_wireless_section","uci","add","wireless",str(section)]
        prtcmd = {"command": "_uci_add_wireless_section", "changes" : str(section)}
        prtcmd = json.dumps(prtcmd)
        self.sending_socket.send("%s %s" %(self.subscription, prtcmd))


    def _bulk_radio_set_command_receive(self, command_json):        
        prtcmd = json.loads(command_json)

    def _radio_set_command_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","set",str(prtcmd[3])])    

    def _generic_set_command_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","set", str(prtcmd[3])])

    def _create_new_section_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","set", str(prtcmd[3])])    

    def _uci_delete_section_name_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","delete", str(prtcmd[3])])    

    def _uci_delete_bss_index_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","delete", str(prtcmd[3])])    

    def _uci_delete_radio_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","delete", str(prtcmd[3])])    

    def _uci_add_wireless_section_receive(self, command_json):
        prtcmd = json.loads(command_json)
        # print "\n  $ "," ".join(prtcmd)
        #subprocess.check_call(["uci","add", str(prtcmd[3])])


    
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
                        command_json  = json.dumps(WARP_response["changes"])
                        getattr(self, "%s_receive" % WARP_response["command"])(command_json)
