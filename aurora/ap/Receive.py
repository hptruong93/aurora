# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys, json, threading, traceback
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

import SliceAgent
from ifconfig import ifconfig
import logging


class Receive():
    """This class connects to RabbitMQ and receives messages containing
    commands, which it executes.  During normal use,
    only this file need be executed on the machine - it will import
    the rest of Aurora and pass the commands along."""

    #### Set the IP of the RabbitMQ host here
    RABBIT_MQ_HOST = '192.168.0.12'

    def __init__(self, queue, config):
        """Connects to RabbitMQ and initializes Aurora locally."""

        # Run Pika logger so that error messages get printed
        logging.basicConfig()

        # Init AP code, pass along any initialization configuration
        self.agent = SliceAgent.SliceAgent(config)
        self.queue = queue

        # Connect to RabbitMQ (Step #1)
        credentials = pika.PlainCredentials('access_point', 'let_me_in')
        self.parameters = pika.ConnectionParameters(host=self.RABBIT_MQ_HOST, credentials=credentials)
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

        # Convert data to JSON
        message = json.loads(body)

        # Prepare JSON data to return
        data_for_sender = {'successful': False, 'message': None, 'ap': self.queue}

        # Execute the command specified
        try:
            return_data = self.agent.execute(**message)

        # If there is an error, let the sender know    
        except Exception as e:

            # Finalize message and convert to JSON
            data_for_sender['message'] = traceback.format_exc()
            data_for_sender = json.dumps(data_for_sender)

            print(" [x] Error; command " + message["command"] + " failed")

        # No error, we (may) return data
        else:

            # Finalize message and convert to JSON
            data_for_sender['successful'] = True
            data_for_sender['message'] = return_data
            data_for_sender = json.dumps(data_for_sender)

            print(" [x] Command executed")


        # Send response
        self.channel.basic_publish(exchange='', routing_key=header.reply_to,
                                    properties=pika.BasicProperties(correlation_id=header.correlation_id,
                                                                    content_type="application/json"),
                                    body=data_for_sender)

# Executed when run from the command line.
# *** NORMAL USAGE ***        
if __name__ == '__main__':

    ######
    # Set the provision server IP/port here
    prov_server = 'http://192.168.0.12:5555/initial_ap_config_request/'
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

    if queue == None:
        raise Exception("AP identifier specified is not valid.")

    print("Joining queue %s" % queue)

    #TODO: Get more from config than just queue name
    # i.e. setup commands, default slice...

    # Establish connection, start listening for commands
    receiver = Receive(queue, config)
    listener = threading.Thread(target=receiver.connection.ioloop.start)
    listener.start()

    # We stop the main thread here, waiting for the user to terminate
    # We cannot use Ctrl-C since it is also recognized by programs such as OVS
    # and all sorts of issues occur when OVS closes before python
    # tries to use OVS to delete bridges
    # We absolutely need a clean exit so that everything can be closed properly
    try:
        raw_input("Press Enter to terminate...\n")
    except:
        # Anything weird happens, ignore (i.e. Ctrl-D = EOF error)
        pass

    # Be nice and let the ioloop know it's time to go
    receiver.channel.basic_cancel()
    receiver.connection.ioloop.stop()

    print("Connections closed.  Cleaning up and exiting.")

