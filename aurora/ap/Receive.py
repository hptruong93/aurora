# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys, pika, json, threading
import SliceAgent
import requests, fcntl, socket, struct

# From http://stackoverflow.com/a/4789267
def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]

class Receive():
    def __init__(self, queue):
        # Init AP code
        self.agent = SliceAgent.SliceAgent()
        self.queue = queue
        
        # Connect to RabbitMQ (Step #1)
        credentials = pika.PlainCredentials('access_point', 'let_me_in')
        self.parameters = pika.ConnectionParameters(host='10.5.8.18', credentials=credentials)
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
        self.channel.queue_declare(queue=self.queue, durable=True, callback=self.on_queue_declared)

    # Step #4
    def on_queue_declared(self, frame):
        """Called when RabbitMQ has told us our Queue has been declared, frame is the response from RabbitMQ"""
        print("Receiver running; waiting for messages.\n")
        self.channel.basic_consume(self.handle_delivery, queue=self.queue)

    # Step #5
    def handle_delivery(self, channel, method, header, body):
        """Called when we receive a message from RabbitMQ.  Executes the command received
        and returns data or an error message if needed."""
        
        # Convert data to JSON
        print " [x] Received %r" % (body,)
        message = json.loads(body)
        
        # Prepare JSON data to return
        data_for_sender = { 'successful' : False, 'message' : None }
        
        # Execute the command specified
        try:
            return_data = self.agent.execute(**message)
        
        # If there is an error, let the sender know    
        except Exception as e:
            
            # Finalize message and convert to JSON
            data_for_sender['message'] = str(type(e)) + " " + str(e)
            data_for_sender = json.dumps(data_for_sender)
            
            # Send response and acknowledge the original message
            self.channel.basic_publish(exchange='', routing_key=header.reply_to, properties=pika.BasicProperties(correlation_id = header.correlation_id, content_type="application/json"), body=data_for_sender )
            self.channel.basic_ack(delivery_tag = method.delivery_tag)
            
            print " [x] Error; command failed"
        
        # No error, we (may) return data
        else:
            
            # Finalize message and convert to JSON
            data_for_sender['successful'] = True
            data_for_sender['message'] = return_data
            data_for_sender = json.dumps(data_for_sender)
            
            # Send response and acknowledge the original message
            self.channel.basic_publish(exchange='', routing_key=header.reply_to, properties=pika.BasicProperties(correlation_id = header.correlation_id, content_type="application/json"), body=data_for_sender )
            self.channel.basic_ack(delivery_tag = method.delivery_tag)
            
            print " [x] Command executed"
        
if __name__ == '__main__':
    # Get mac address
    mac = getHwAddr("eth0")
    # Put in HTTP request to get config
    request = requests.get('http://10.5.8.18:5555/initial_ap_config_request/' + mac)
    queue = request.json()["queue"]
    if queue == null:
        raise Exception("AP identifier specified is not valid.")
    
    
    # Establish connection, start listening for commands
    receiver = Receive(queue)
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
    # Alternatively, you could specify listener as a daemon
    # which will be forcibly killed when python exits
    # This is untested and may cause socket issues however
    receiver.connection.ioloop.poller.open = False

