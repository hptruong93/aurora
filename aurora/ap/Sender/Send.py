# Test Class for JSON message passing (SEND)
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys, uuid
import pika
import json

class Send(object):
          
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.5.8.18'))
        self.channel = self.connection.channel()
        
        response = self.channel.queue_declare(exclusive=True)
        self.callback_queue = response.method.queue
        
        self.channel.basic_consume(self.process_response, no_ack=True, queue=self.callback_queue)
        
        
    def process_response(self, channel, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body
    
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
            self.channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(reply_to = self.callback_queue, correlation_id = self.corr_id, content_type="application/json"))
            print " [x] Sent %r" % (message,)
        
            while self.response is None:
               self.connection.process_data_events()
            print(self.response)
            


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
        else:
            print('Invalid choice')
            
