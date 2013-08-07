# Test Class for JSON message passing (SEND)
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys
import pika
import json

class JSONSend():
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='task_queue', durable=True)
        try:
            JFILE = open('message.json', 'r')
            self.temp = json.load(JFILE)
        except:
            print('Error loading json file!')
            sys.exit(-1)
        
    def send(self):
        self.message = json.dumps(self.temp)
        self.channel.basic_publish(exchange='', routing_key='task_queue', body=self.message, properties=pika.BasicProperties(delivery_mode = 2))
        print " [x] Sent %r" % (self.message,)
        return

JSONSend().send()
