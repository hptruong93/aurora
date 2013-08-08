# Test Class for JSON message passing (RECEIVE)
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys
import pika
import json
import SliceAgent

class Receive():
    def __init__(self):
        self.agent = SliceAgent.SliceAgent()
        self.connection = pika.SelectConnection(pika.ConnectionParameters(host='10.5.8.18'))
        self.channel = self.connection.channel(None)
        self.channel.queue_declare(self.receive,queue='task_queue', durable=True)
        
    def declare_queue(channel)    
    
    def receive(self):
        print ' [*] Waiting for messages. To exit press CTRL+C'
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(self.callback, queue='task_queue')
        self.channel.start_consuming()
    
    def callback(self, ch, method, properties, body):
        print " [x] Received %r" % (body,)
        message = json.loads(body) #Received JSON
        
        try:
            self.agent.execute(**message)
        except:
            # In the future, we will return an error message
            pass
        print " [x] Command executed"
        ch.basic_ack(delivery_tag = method.delivery_tag)
        
Receive()
raw_input("Press a key to terminate...")
