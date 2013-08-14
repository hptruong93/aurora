# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys, uuid, pika, json
import threading

class Send(object):
          
    def __init__(self):
        """Establishes the connection to RabbitMQ and sets up the queues"""
        credentials = pika.PlainCredentials('outside_world', 'wireless_access')
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='132.206.206.137', credentials=credentials))
        self.channel = self.connection.channel()
        
        response = self.channel.queue_declare(exclusive=True)
        self.callback_queue = response.method.queue
        
        self.channel.basic_consume(self.process_response, queue=self.callback_queue)
        
        # Create dictionary for correlation ID
        self.corr_id = {}
        
        # Start listening for callbacks
        listener = threading.Thread(target=self.channel.start_consuming)
        listener.start()
        
        
    def process_response(self, channel, method, props, body):
        """Processes any responses it sees, checking to see if the
        correlation ID matches one sent.  If it does, the response
        is displayed along with the request originally sent."""
        if props.correlation_id in self.corr_id:
            response_decoded = json.loads(body)
            
            ap = self.corr_id[props.correlation_id][0]
            sent_data = self.corr_id[props.correlation_id][1]
            print("Response received for command " + sent_data + " to AP " + ap)
            
            # Display appropriate message
            if response_decoded['successful']:
                print("Command successful; returned\n" + str(response_decoded['message']))
            else:
                print("Error: " + str(response_decoded['message']))
            
            # Delete correlation entry
            del self.corr_id[props.correlation_id]
       
        # We acknowledge all messages, even if the correlation ID does not exist
        # Since the queue is unique to us, the response is likely a resend
        # This can happen if the AP dies right after it sends the response but before it sends
        # an acknowledgement to RabbitMQ saying that it processed the original message
        # This is very unlikely, but possible      
        channel.basic_ack(delivery_tag = method.delivery_tag)
    
    
    def send(self, data, ap):
        """Send data to the specified access point."""
    
        # Load JSON
        try:
             JFILE = open(data, 'r')
             temp = json.load(JFILE)
        except:
            print('Error loading json file, not sending')
        else:
            
            # Convert JSON to string 
            message = json.dumps(temp)
            
            # Generate random ID, add to dictionary
            correlation_id = str(uuid.uuid4())
            self.corr_id[correlation_id] = [ ap, message ]
            
            # Send JSON
            # We attach a reply_to and correlation ID to tell the AP to send a message to the queue we create (randomly generated name) at init
            # with the correlation id specified.  This means that 
            # a) we get the message, since it is on the right queue
            # b) the message is not on the AP queue, thus not confusing any other APs - this queue is exclusive to this sender
            # c) we can tie the message sent to the message received later since they have the same correlation ID
            # See http://www.rabbitmq.com/tutorials/tutorial-six-python.html for more info
            
            self.channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(reply_to = self.callback_queue, correlation_id = correlation_id, content_type="application/json"))
            print("Message in file " + data + " sent.")


# Menu loop; thanks Kevin
if __name__ == '__main__':
    exitLoop = False
    sender = Send()
    while not exitLoop:
        print('Choose an option: ')
        print('1. Create slices 1 and 2 on AP1')
        print('2. Create slices 1 and 2 on AP2')
        print('3. Create slices 1 and 2 on AP3')
        print('4. Delete slices 1 and 2 on AP1')
        print('5. Delete slices 1 and 2 on AP2')
        print('6. Delete slices 1 and 2 on AP3')
        print('7. Send test.json to test')
        print('8. Send test2.json to test')
        print('9. Create slices 1 and 2 on APs 1-3')
        print('10. Delete slices 1 and 2 on APs 1-3')
        print('0. Exit')
        choice = raw_input()
        if choice == '0':
            exitLoop = True
            # Stop listening for replies
            sender.channel.stop_consuming()
        elif choice == '1':
            sender.send('ap-slice1.json','ap1')
            sender.send('ap-slice2.json','ap1')
        elif choice == '2':
            sender.send('ap2-slice1.json','ap2')
            sender.send('ap2-slice2.json','ap2')
        elif choice == '3':
            sender.send('ap3-slice1.json','ap3')
            sender.send('ap3-slice2.json','ap3')
        elif choice == '4':
            sender.send('delete-slice1.json','ap1')
            sender.send('delete-slice2.json','ap1')
        elif choice == '5':
            sender.send('delete-slice1.json','ap2')
            sender.send('delete-slice2.json','ap2')
        elif choice == '6':
            sender.send('delete-slice1.json','ap3')
            sender.send('delete-slice2.json','ap3')
        elif choice == '7':
            sender.send('test.json','test')
        elif choice == '8':
            sender.send('test2.json','test')
        elif choice == '9':
            sender.send('ap-slice1.json','ap1')
            sender.send('ap-slice2.json','ap1')
            sender.send('ap2-slice1.json','ap2')
            sender.send('ap2-slice2.json','ap2')
            sender.send('ap3-slice1.json','ap3')
            sender.send('ap3-slice2.json','ap3')
        elif choice == '10':
            sender.send('delete-slice1.json','ap1')
            sender.send('delete-slice2.json','ap1')
            sender.send('delete-slice1.json','ap2')
            sender.send('delete-slice2.json','ap2')
            sender.send('delete-slice1.json','ap3')
            sender.send('delete-slice2.json','ap3')
            
        else:
            print('Invalid choice')
            
