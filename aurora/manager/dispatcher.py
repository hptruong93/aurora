import sys, pika, json
import threading
from threading import Timer
import resource_monitor

class Dispatcher():

    TIMEOUT = 30
    
    def __init__(self):
        """Establishes the connection to RabbitMQ and sets up the queues"""
        credentials = pika.PlainCredentials('outside_world', 'wireless_access')
        self.connection = pika.SelectConnection(pika.ConnectionParameters(host='132.206.206.137', credentials=credentials), self.on_connected)
        
        # Create dictionary for requests sent out
        self.requests_sent = []
        
        self.resourceMonitor = resource_monitor.resourceMonitor(self)
        
        # Setup complete, now start listening and processing
        # This jumpstarts the connection, which in turn uses the callbacks
        self.connection.connect()
        listener = threading.Thread(target=self.connection.ioloop.start)
        listener.start()
        
    
    def channel_open(self, new_channel):
        self.channel = new_channel
        response = self.channel.queue_declare(exclusive=True, callback=self.on_queue_declared)
        
    
    def on_queue_declared(self, frame):
        self.callback_queue = frame.method.queue
        self.channel.basic_consume(self.process_response, queue=self.callback_queue)
        
    
    def on_connected(self, connection):
        self.connection.channel(self.channel_open)
    
    def dispatch(self, config, ap, unique_id):
        """Send data to the specified queue.
        Note that the caller is expected to set database
        properties such as status.
        
        NOTE: unique_id *MUST* be more than 1 character
        due to a Python bug."""
        # Convert JSON to string 
        message = json.dumps(config)
            
        self.requests_sent.append(unique_id)
            
        # Send JSON
        # We attach a reply_to and correlation ID to tell the AP to send a message to the queue we create (randomly generated name) at init
        # with the correlation id specified.  This means that 
        # we can see if our request executed successfully or not
        # See http://www.rabbitmq.com/tutorials/tutorial-six-python.html for more info
            
        self.channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(reply_to = self.callback_queue, correlation_id = unique_id, content_type="application/json"))
        
        print("Message for %s dispatched" % ap)
        
        # Start a timeout countdown
        time = Timer(self.TIMEOUT, self.resourceMonitor.timeout, args=[unique_id])
        self.requests_sent.append( (unique_id,time) )

        time.start()


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
            self.resourceMonitor.set_status(props.correlation_id, decoded_response['successful'])
            
            
            # Note: This will throw an exception if the unique_id used
            # in the original request is only 1 character long, as python
            # decides to create a string rather than a tuple
            # and access to the timer object is lost
            # Workaround: try/catch
            try:
                entry[1].cancel()
            except Exception:
                pass
            
            self.requests_sent.remove(entry)
        
        else:

            decoded_response = json.loads(body)
            
            self.resourceMonitor.reset_AP(decoded_response['ap'])
            
            
        # Regardless of content of message, acknowledge receipt of it
        channel.basic_ack(delivery_tag = method.delivery_tag)
    
    def stop(self):
        self.channel.basic_cancel()
        self.connection.ioloop.stop()
     


# Menu loop; thanks Kevin
# Obviously this code will not be in a final version
if __name__ == '__main__':
    exitLoop = False
    sender = Dispatcher()

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
            except IOError:
                print('Bad file, returning to menu')
            else:
                config = json.load(file)
                file.close()
                print('Enter ap ID')
                ap = raw_input()
                print('Enter unique id')
                unique_id = raw_input()
                sender.dispatch( config, ap, unique_id)

            
