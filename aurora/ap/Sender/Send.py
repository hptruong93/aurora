# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys, uuid
import pika
import json
import datetime

class Send(object):
          
    def __init__(self):
        """Establishes the connection to RabbitMQ and sets up the queues"""
        credentials = pika.PlainCredentials('outside_world', 'wireless_access')
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='132.206.206.137',credentials=credentials))
        self.channel = self.connection.channel()
        
        response = self.channel.queue_declare(exclusive=True)
        self.callback_queue = response.method.queue
        
        self.channel.basic_consume(self.process_response, queue=self.callback_queue)
        
        
    def process_response(self, channel, method, props, body):
        """Processes any responses it sees, checking to see if the
        correlation ID matches."""
        if self.corr_id == props.correlation_id:
            self.response = body
        # For now we acknowledge all messages, even those we discard
        # In the future where we might send one message to many APs
        # at once, we will have to process differently
        channel.basic_ack(delivery_tag = method.delivery_tag)
    
    def process_reject(self, channel, method, props, body):
        print("[x] Server rejected message; aborting. Rejected Message: \n" + str(body))
    
    
    def send(self, data, ap):
        
        self.response = None
        self.corr_id = str(uuid.uuid4())

        try:
             JFILE = open(data, 'r')
             temp = json.load(JFILE)
        except:
            print('Error loading json file, not sending')
        else:
            
            message = json.dumps(temp)
            start_time = datetime.datetime.now()
            self.channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(reply_to = self.callback_queue, correlation_id = self.corr_id, content_type="application/json"))
            print " [x] Sent %r" % (message,)
        
            # Wait for a response
            while self.response is None:
               self.connection.process_data_events()
            duration = datetime.datetime.now() - start_time
            print("Response received in " + str(duration.microseconds) + " us")
            # Display message to user
            response_decoded = json.loads(self.response)
            if response_decoded['successful']:
                print("Command successful; returned\n" + str(response_decoded['message']))
            else:
                print("Error: " + str(response_decoded['message']))
            


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
            
