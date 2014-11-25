"""Receive module fetches access point configuration from manager's 
provision server and sets up access point message queues.  It passes 
received message content to SliceAgent.

"""
#!/usr/bin/python -tt
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys
import json
import threading
import os
import signal
import time
import traceback
import inspect

import config as init_info
import install_dependencies

from pprint import pprint
from ifconfig import ifconfig

try:
    import pika
except ImportError:
    print "Module pika not found. Installing pika..."
    install_dependencies.install("pika")
    import pika

try:
    import requests
except ImportError:
    install_dependencies.install("requests")
    import requests

import SliceAgent
import logging

def ln(stringhere = 'was here', number_of_dash = 40):
    print("%s:%s %s> %s"% (__file__, inspect.currentframe().f_back.f_lineno, '-'*number_of_dash, stringhere))

class Receive():
    """This class connects to RabbitMQ and receives messages containing
    commands, which it executes.  During normal use,
    only this file need be executed on the machine - it will import
    the rest of Aurora and pass the commands along."""
    
    def __init__(self, region, queue, config, rabbitmq_host, rabbitmq_username, rabbitmq_password, rabbitmq_reply_queue):
        """Connects to RabbitMQ and initializes Aurora locally."""
        
        # Run Pika logger so that error messages get printed
        logging.basicConfig()

        # Init AP code, pass along any initialization configuration
        self.agent = SliceAgent.SliceAgent(config)
        self.queue = queue
        self.region = region
        self.manager_queue = rabbitmq_reply_queue
        self.channel_open = False
   
        # Connect to RabbitMQ (Step #1)
        print "Connecting to RabbitMQ server with host = %s and credentials = username:\"%s\", password:\"%s\"" % (rabbitmq_host, rabbitmq_username, rabbitmq_password)
        credentials = pika.PlainCredentials(rabbitmq_username, rabbitmq_password)
        self.parameters = pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials)
        self.connection = pika.SelectConnection(self.parameters, on_open_callback=self.on_connected)

        self.listener = threading.Thread(target=self.connection.ioloop.start)
        self.listener.start()


    # Step #2
    def on_connected(self, connection):
        """Called when we are fully connected to RabbitMQ"""
        print "Connected. Opening a channel..."
        # Open a channel
        self.connection.channel(self.on_channel_open)

    # Step #3
    def on_channel_open(self, new_channel):
        """Called when our channel has opened"""
        self.channel = new_channel
        # Queue set to delete if this consumer dies, to be volatile (RabbitMQ dies -> takes queue with it)
        # and to not require acknowledgements.  All of these are useful if you want to preserve messages,
        # but it is likely that any preserved messages will take longer than the timeout on the manager
        # to be delivered and processed (i.e. OS reboot, RabbitMQ restart, etc.) and will put the AP
        # into some state unknown to the manager.  Thus, we discard them if anything ever goes wrong

        # Note: no_ack set in on_queue_declared
        print "Channel opened. Declaring queue %s..." % self.queue
        self.channel.queue_declare(queue=self.queue, durable=False, callback=self.on_queue_declared, auto_delete=True)

    # Step #4
    def on_queue_declared(self, frame):
        """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
        self.channel_open = True
        print "Queue declared. Declaring consumption call back..."
        self.channel.basic_consume(self.handle_delivery, queue=self.queue, no_ack=True,)

    # Step #5
    def handle_delivery(self, channel, method, header, body):
        """Called when we receive a message from RabbitMQ.  Executes the command received
        and returns data or an error message if needed."""
        print "Receiving... \n%s" % body
        
        print channel
        print method
        print header
        print body
        if header.reply_to != self.manager_queue:
            self.manager_queue = header.reply_to
        
        
        # Convert data to JSON
        message = json.loads(body)

        # Prepare JSON data to return
        data_for_sender = {'successful': False, 'message': None, 'config': {}, 'ap': self.queue}

        # Execute the command specified
        try:
            return_data = None
            if message['command'] == 'SYN':
                return_data = 'SYN/ACK'
            else:
                ln("We need to change something here?")
                return_data = self.agent.execute(**message)
        # If there is an error, let the sender know    
        except Exception as e:
            # Finalize message and convert to JSON
            data_for_sender['message'] = traceback.format_exc()
            traceback.print_exc()
            print(" [x] Error; command %s failed\n%s" % (message["command"], e.message))

        else:
            # No error, we (may) return data.
            # Finalize message and convert to JSON
            data_for_sender['successful'] = True
            data_for_sender['message'] = return_data

            print(" [x] Command executed")

        data_for_sender['self.config'] = {}
        data_for_sender['config']['init_database'] = self.agent.database.database
        data_for_sender['config']['init_user_id_database'] = self.agent.database.user_id_data
        data_for_sender['config']['init_hardware_database'] = self.agent.database.hw_database
        data_for_sender['config']['region'] = self.region
        data_for_sender = json.dumps(data_for_sender)
        # Send response
        self.channel.basic_publish(exchange='', routing_key=header.reply_to,
                                    properties=pika.BasicProperties(correlation_id=header.correlation_id,
                                                                    content_type="application/json"),
                                    body=data_for_sender)

    
    
    def send_ap_up_status(self, config):
        print "Sending up status..."
        
        waiting_count = 0
        while not self.channel_open:
            print "Waiting for channel... Waiting count %s" % waiting_count
            waiting_count += 1
            time.sleep(0.2)

        print "AP up - alerting manager...",
        slices_to_recreate = []
        if 'init_database' in config['last_known_config']:
            if len(config['last_known_config']['init_database']) > 1:
                slices_to_recreate = []
                last_db_config = config['last_known_config']['init_database']
                main_slice = self.agent.database.find_main_slice(
                    last_db_config
                )
                if not main_slice:
                    print "\nError: No slice with radio profile"
                    return
                slices_to_recreate.append(main_slice)
                
                for key in last_db_config.keys():
                    if key != "default_slice" and key != main_slice:
                        slices_to_recreate.append(key)

        data_for_sender = {"successful":True,
                           "message":"SYN",
                           "config":{},
                           "slices_to_recreate":slices_to_recreate,
                           "ap":self.queue}
        data_for_sender['config']['init_database'] = self.agent.database.database
        data_for_sender['config']['init_user_id_database'] = self.agent.database.user_id_data
        data_for_sender['config']['init_hardware_database'] = self.agent.database.hw_database
        data_for_sender['config']['region'] = self.region
        data_for_sender = json.dumps(data_for_sender)
        try:
            self.channel.basic_publish(exchange='', routing_key=self.manager_queue,
                                   properties=pika.BasicProperties(content_type="application/json"),
                                   body=data_for_sender)
            pass
        except:
            traceback.print_exc(file=sys.stdout)
        return

    def shutdown_signal_received(self):
        ln("To do: send shutdown information to lower modules to close thread in WARPRadio")

        current_database = {}
        current_database['init_database'] = self.agent.database.database
        current_database['init_user_id_database'] = self.agent.database.user_id_data
        current_database['init_hardware_database'] = self.agent.database.hw_database
        current_database['region'] = self.region

        print("Sending current database...\n%s" % current_database)

        data_for_sender = {'successful':True, 'message': 'FIN', 'config': current_database, 'ap': self.queue}
        data_for_sender = json.dumps(data_for_sender)
        
        try:
            self.channel.basic_publish(exchange='', routing_key=self.manager_queue,
                                    properties=pika.BasicProperties(content_type="application/json"),
                                    body=data_for_sender)
        except:
            traceback.print_exc(file=sys.stdout)
        

# Executed when run from the command line.
# *** NORMAL USAGE ***        
if __name__ == '__main__':

    ## Working directory for all files
    os.chdir('/usr/aurora')

    ######
    # Set the provision server IP/port here
    prov_server = 'http://%s:%s/initial_ap_config_request/' % (init_info.CONFIG['init_config']['manager'], init_info.CONFIG['init_config']['manager_port'])
    #######

    # Get mac address
    mac = ifconfig(init_info.CONFIG['init_config']['ethernet_interface'])["hwaddr"]
    # Put in HTTP request to get config
    try:
        request = requests.get(prov_server + mac)
    except requests.exceptions.ConnectionError:
        print("Unable to connect to provision server @ " + prov_server)
        exit()

    config_full = request.json()
    queue = config_full['queue']
    if 'region' in config_full.keys():
        region = config_full['region']
    else:
        region = None
    config = {}
    config['default_config'] = config_full['default_config']
    try:
        config['last_known_config'] = config_full['last_known_config']
    except:
        config['last_known_config'] = {}
    username = config_full['rabbitmq_username']
    password = config_full['rabbitmq_password']
    rabbitmq_host = config_full['rabbitmq_host']
    rabbitmq_reply_queue = config_full['rabbitmq_reply_queue']

    if queue == None:
        raise Exception("AP identifier specified is not valid.")

    print("Joining queue %s" % queue)
    # Establish connection, start listening for commands
    receiver = Receive(region, queue, config, rabbitmq_host, 
                       username, password, rabbitmq_reply_queue)

    
    attempt = 0
    while not receiver.channel_open:
        print("Waiting for connection... Attempt number %s" % attempt)
        attempt += 1
        time.sleep(1)

    receiver.send_ap_up_status(config)

    # Thanks to Matt J http://stackoverflow.com/a/1112350
    def signal_handler(signal, frame):
        # Be nice and let the ioloop know it's time to go
    #    receiver.channel.basic_cancel()
    #    receiver.connection.ioloop.stop()
        receiver.shutdown_signal_received()
        time.sleep(1)
        receiver.connection.close()
        print("Connections closed.  Cleaning up and exiting.")
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()