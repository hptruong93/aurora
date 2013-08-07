# Test Class for JSON message passing (RECEIVE)
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys
import pika
import json

class JSONReceive():
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='task_queue', durable=True)
        
    def receive(self):
        print ' [*] Waiting for messages. To exit press CTRL+C'
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self.callback, queue='task_queue')
        self.channel.start_consuming()
    
    def callback(self, ch, method, properties, body):
        print " [x] Received %r" % (body,)
        message = json.loads(body) #THIS IS THE RECEIVED JSON FILE LOADED INTO MEMORY
        print message['VirtInterfaces']
        print " [x] Done"
        ch.basic_ack(delivery_tag = method.delivery_tag)
        
JSONReceive().receive()
