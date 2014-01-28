# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys, json, threading, traceback, os, signal, time
import install_dependencies

try:
    import pika
except ImportError:
    install_dependencies.install("pika")
    import pika

try:
    import requests
except ImportError:
    install_dependencies.install("requests")
    import requests

try:
    from ifconfig import ifconfig
except ImportError:
    install_dependencies.install("python-ifconfig")
    from ifconfig import ifconfig

import SliceAgent
import logging


class Receive():
    """This class connects to RabbitMQ and receives messages containing
    commands, which it executes.  During normal use,
    only this file need be executed on the machine - it will import
    the rest of Aurora and pass the commands along."""

    def __init__(self, queue, config, rabbitmq_host, rabbitmq_username, rabbitmq_password, rabbitmq_reply_queue):
        """Connects to RabbitMQ and initializes Aurora locally."""

        # Run Pika logger so that error messages get printed
        logging.basicConfig()

        # Init AP code, pass along any initialization configuration
        self.agent = SliceAgent.SliceAgent(config)
        self.queue = queue
        self.manager_queue = rabbitmq_reply_queue

        # Connect to RabbitMQ (Step #1)
        credentials = pika.PlainCredentials(rabbitmq_username, rabbitmq_password)
        self.parameters = pika.ConnectionParameters(host=rabbitmq_host, credentials=credentials)
        self.connection = pika.SelectConnection(self.parameters, self.on_connected)

    
    # Step #2
    def on_connected(self, connection):
        """Called when we are fully connected to RabbitMQ"""
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
        self.channel.queue_declare(queue=self.queue, durable=False, callback=self.on_queue_declared,
                                   auto_delete=True)

    # Step #4
    def on_queue_declared(self, frame):
        """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
        self.channel.basic_consume(self.handle_delivery, queue=self.queue, no_ack=True,)

    # Step #5
    def handle_delivery(self, channel, method, header, body):
        """Called when we receive a message from RabbitMQ.  Executes the command received
        and returns data or an error message if needed."""
        print "Receiving..."
        
        #print channel
        #print method
        #print header
        #print body
        if header.reply_to != self.manager_queue:
            self.manager_queue = header.reply_to
        
        
        # Convert data to JSON
        message = json.loads(body)

        # Prepare JSON data to return
        data_for_sender = {'successful': False, 'message': None, 'config': None, 'ap': self.queue}

        # Execute the command specified
        try:
            return_data = self.agent.execute(**message)

        # If there is an error, let the sender know    
        except Exception as e:
            # Finalize message and convert to JSON
            data_for_sender['message'] = traceback.format_exc()

            print(" [x] Error; command " + message["command"] + " failed\n" + e.message)

        # No error, we (may) return data
        else:

            # Finalize message and convert to JSON
            data_for_sender['successful'] = True
            data_for_sender['message'] = return_data

            print(" [x] Command executed")

        data_for_sender['config'] = self.agent.database
        print data_for_sender
        data_for_sender = json.dumps(data_for_sender)
        # Send response
        self.channel.basic_publish(exchange='', routing_key=header.reply_to,
                                    properties=pika.BasicProperties(correlation_id=header.correlation_id,
                                                                    content_type="application/json"),
                                    body=data_for_sender)

    def shutdown_signal_received(self):
        current_database = self.agent.database
        print "Sending current database..."
        print current_database
        data_for_sender = {'successful':True, 'message': 'FIN', 'config': current_database, 'ap': self.queue}
        data_for_sender = json.dumps(data_for_sender)
        self.channel.basic_publish(exchange='', routing_key=self.manager_queue,
                                    properties=pika.BasicProperties(content_type="application/json"),
                                    body=data_for_sender)

# Executed when run from the command line.
# *** NORMAL USAGE ***        
if __name__ == '__main__':

    ## Working directory for all files
    os.chdir('/usr/aurora')

    ######
    # Set the provision server IP/port here
    prov_server = 'http://10.5.8.3:5555/initial_ap_config_request/'
    #######

    # Get mac address
    mac = ifconfig("eth0")["hwaddr"]
    # Put in HTTP request to get config
    try:
        request = requests.get(prov_server + mac)
    except requests.exceptions.ConnectionError:
        print("Unable to connect to provision server @ " + prov_server)
        exit()

    config_full = request.json()
    queue = config_full['queue']
    config = config_full['default_config']
    username = config_full['rabbitmq_username']
    password = config_full['rabbitmq_password']
    rabbitmq_host = config_full['rabbitmq_host']
    rabbitmq_reply_queue = config_full['rabbitmq_reply_queue']

    if queue == None:
        raise Exception("AP identifier specified is not valid.")

    print("Joining queue %s" % queue)
    # Establish connection, start listening for commands
    receiver = Receive(queue, config, rabbitmq_host, username, password, rabbitmq_reply_queue)

    listener = threading.Thread(target=receiver.connection.ioloop.start)
    listener.start()

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

        
        
        
        
    
