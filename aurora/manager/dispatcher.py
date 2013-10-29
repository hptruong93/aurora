import sys, pika, json
import threading, resource_monitor

class Dispatcher():

    TIMEOUT = 30
    
    def __init__(self):
        """Establishes the connection to RabbitMQ and sets up the queues"""
        credentials = pika.PlainCredentials('outside_world', 'wireless_access')
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='132.206.206.137', credentials=credentials))
        self.channel = self.connection.channel()
        
        response = self.channel.queue_declare(exclusive=True)
        self.callback_queue = response.method.queue
        
        self.channel.basic_consume(self.process_response, queue=self.callback_queue)
        
        # Create dictionary for requests sent out
        self.requests_sent = []
        
        # Start listening for callbacks
        listener = threading.Thread(target=self.channel.start_consuming)
        listener.start()
        
        self.resourceMonitor = resource_monitor.resourceMonitor()
        
    def dispatch(self, config, ap, unique_id):
        """Send data to the specified queue.
        Note that the caller is expected to set database
        properties such as status."""
        # Convert JSON to string 
        message = json.dumps(config)
            
        self.requests_sent.append(unique_id)
            
        # Send JSON
        # We attach a reply_to and correlation ID to tell the AP to send a message to the queue we create (randomly generated name) at init
        # with the correlation id specified.  This means that 
        # we can see if our request executed successfully or not
        # See http://www.rabbitmq.com/tutorials/tutorial-six-python.html for more info
            
        self.channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(reply_to = self.callback_queue, correlation_id = unique_id, content_type="application/json"))
        
        print("Message for %s dispatched" % unique_id)
        
        # Start a timeout countdown
        time = Timer(self.TIMEOUT, timeout, args=[unique_id])
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
        # to cause it to wait so long. Problem is we don't know what AP....

        # Check if we have a record of this ID
        have_request = False
        for request in self.requests_sent:
            if request[0] == props.correlation_id:
                have_request = True
                break
                
        if have_request:
            # ACK request
            channel.basic_ack(delivery_tag = method.delivery_tag)
            # Decode response
            decoded_response = json.loads(body)

            # Set status, stop timer, delete record
            resourceMonitor.set_status(props.correlation_id, decoded_response['successful'])
            
            request[1].cancel()
            self.requests_sent.remove(request)
        else:
            #TODO: (if possible): Identify AP that sent bad messsage and reset it
            
            
        # Even if the message is bogus, acknowledge receipt of it
        channel.basic_ack(delivery_tag = method.delivery_tag)
    
     


# Menu loop; thanks Kevin
if __name__ == '__main__':
    exitLoop = False
    sender = Send()
    while not exitLoop:
        print('Choose an option: ')
        print('1. Create slices 1 and 2 on AP1')
        choice = raw_input()
        if choice == '0':
            exitLoop = True
            # Stop listening for replies
            sender.channel.stop_consuming()
        elif choice == '1':
            sender.send('ap-slice1.json','ap1')

            
