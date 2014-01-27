import sys, pika, json
import threading
from threading import Timer
import resource_monitor
import logging
import provision_server.ap_provision as provision

class Dispatcher():
    lock = None
    TIMEOUT = 30
    
    def __init__(self, host, username, password, mysql_username, mysql_password):
        """Establishes the connection to RabbitMQ and sets up the queues"""
        
        print "Constructing Dispatcher..."
        # Run Pika logger so that error messages get printed
        logging.basicConfig()

        credentials = pika.PlainCredentials(username, password)
        self.connection = pika.SelectConnection(pika.ConnectionParameters(host=host, credentials=credentials), self.on_connected)
        
        # Create dictionary for requests sent out
        self.requests_sent = []
        
        self.resourceMonitor = resource_monitor.resourceMonitor(self, host, mysql_username, mysql_password)
        
        # Setup complete, now start listening and processing
        # This jumpstarts the connection, which in turn uses the callbacks
        # Note: connect() is called automatically in SelectConnection().__init__()
        #
        # self.connection.connect()
        Dispatcher.lock = False
        # Start ioloop, this will quit by itself when Dispatcher().stop() is run
        self.listener = threading.Thread(target=self.connection.ioloop.start)
        self.listener.start()
        
        
    def __del__(self):
        print "Deconstructing Dispatcher..."
    
    def channel_open(self, new_channel):
        self.channel = new_channel
        response = self.channel.queue_declare(exclusive=True, durable=True, callback=self.on_queue_declared)
        
    
    def on_queue_declared(self, frame):
        self.callback_queue = frame.method.queue
        self.channel.basic_consume(self.process_response, queue=self.callback_queue)
        
    
    def on_connected(self, connection):
        self.connection.channel(self.channel_open)
    
    def dispatch(self, config, ap, unique_id):
        """Send data to the specified queue.
        Note that the caller is expected to set database
        properties such as status."""
        # Convert JSON to string 
        message = json.dumps(config)

        # Send JSON
        # We attach a reply_to and correlation ID to tell the AP to send a message to the queue we create (randomly generated name) at init
        # with the correlation id specified.  This means that 
        # we can see if our request executed successfully or not
        # See http://www.rabbitmq.com/tutorials/tutorial-six-python.html for more info
        if Dispatcher.lock:
            print " [x] Dispatch: Dispatcher locked, waiting..."
            while Dispatcher.lock:
                pass
        print " [x] Dispatch: Locking..."
        Dispatcher.lock = True
        self.channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(reply_to = self.callback_queue, correlation_id = unique_id, content_type="application/json"))
        
        print("Message for %s dispatched" % ap)

        ap_slice_id = config['slice']
        # Start a timeout countdown
        print "ap_slice_id >>>",ap_slice_id
        time = Timer(self.TIMEOUT, self.resourceMonitor.timeout, args=(ap_slice_id,))

        self.requests_sent.append((unique_id, time, ap_slice_id))
        time.start()
        #print "Starting timer:",self.requests_sent[-1]
        
        print " [x] Dispatch: Unlocking..."
        Dispatcher.lock = False


    def process_response(self, channel, method, props, body):
        """Processes any responses it sees, checking to see if the
        correlation ID matches one sent.  If it does, the response
        is displayed along with the request originally sent."""
        
        # Basic Proof-of-Concept Implementation
        # 1. We dispatch (see method above)
        # 2. Response received: if related to a request we sent out, OK
        # ACK it
        # Update database to reflect content (i.e. success or error)
        
        # If we don't have a record, that means that we already
        # handled a timeout previously and something strange happened to the AP
        # to cause it to wait so long. Reset it.

        # Check if we have a record of this ID
        have_request = False
        entry = None
        
        if Dispatcher.lock:
            print " [x] Response: Dispatcher locked, waiting..."
            while Dispatcher.lock:
                pass

        #print "channel:",channel
        #print "method:", method
        print repr(props)
        print body
        #print "\nrequests_sent:",self.requests_sent
        

        
        for request in self.requests_sent:
            if request[0] == props.correlation_id:
                have_request = True
                entry = request
                break
                
        if have_request:

            # Decode response
            decoded_response = json.loads(body)
            
            print(' [x] DEBUG: Printing received message')
            print(decoded_response['message'])

            # Set status, stop timer, delete record
            #print "entry[2]:",entry[2]
            if entry[2] != 'admin':
                self.resourceMonitor.set_status(entry[2], decoded_response['successful'])
            else:
                #Probably a reset or restart command sent from resource_monitor
                #Just stop timer and remove entry
                pass
                
            
            entry[1].cancel()
            
            self.requests_sent.remove(entry)
        
        else:

            decoded_response = json.loads(body)
            print " [x] Sending reset to '%s'" % decoded_response['ap']
            # Reset the access point
            self.resourceMonitor.reset_AP(decoded_response['ap'])
            
            
        # Regardless of content of message, acknowledge receipt of it
        channel.basic_ack(delivery_tag = method.delivery_tag)
    
    def stop(self):
        # SelectConnection object close method cancels ioloop and cleanly
        # closes associated channels
        # Stop timers
        for entry in self.requests_sent:
            print " [x] Cancelling timer %s" % entry[1]
            entry[1].cancel()
        self.connection.close()
     


# Menu loop; thanks Kevin
# Obviously this code will not be in a final version
if __name__ == '__main__':
    exitLoop = False

    ######
    # Connection Variables
    host = 'localhost'
    username = 'outside_world'
    password = 'wireless_access'
    mysql_username = 'root'
    mysql_password = 'supersecret'
    sender = Dispatcher(host, username, password, mysql_username, mysql_password)
    provision.run()

    while not exitLoop:
        print('Choose an option: ')
        print('0. Exit')
        print('1. Dispatch')
        choice = raw_input()
        if choice == '0':
            exitLoop = True
            # Stop listening for replies
            sender.stop()
            
        elif choice == '1':
            print('Enter json filename')
            try:
                file = open(raw_input())
                config = json.load(file)
                file.close()
            except:
                print('Bad file, returning to menu')
            else:

                print('Enter ap ID')
                ap = raw_input()
                print('Enter unique id')
                unique_id = raw_input()
                sender.dispatch( config, ap, unique_id)

    provision.stop()
