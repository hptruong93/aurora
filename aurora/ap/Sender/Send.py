# Test Class for JSON message passing (SEND)
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith

import sys
import pika
import json

        
def send(data, ap):
        
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.5.8.18'))
    channel = connection.channel()
    channel.queue_declare(queue=ap, durable=True)
    try:
         JFILE = open(data, 'r')
         temp = json.load(JFILE)
    except:
        print('Error loading json file!')
        sys.exit(-1)
    
    message = json.dumps(temp)
    channel.basic_publish(exchange='', routing_key=ap, body=message, properties=pika.BasicProperties(delivery_mode = 2))
    print " [x] Sent %r" % (message,)


# Menu loop; thanks Kevin
if __name__ == '__main__':
    exitLoop = False
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
            send('ap-slice1.json','ap1')
            send('ap-slice2.json','ap1')
        elif choice == '2':
            send('ap2-slice1.json','ap2')
            send('ap2-slice2.json','ap2')
        elif choice == '3':
            send('ap3-slice1.json','ap3')
            send('ap3-slice2.json','ap3')
        elif choice == '4':
            send('delete-slice1.json','ap1')
            send('delete-slice2.json','ap1')
        elif choice == '5':
            send('delete-slice1.json','ap2')
            send('delete-slice2.json','ap2')
        elif choice == '6':
            send('delete-slice1.json','ap3')
            send('delete-slice2.json','ap3')
        elif choice == '7':
            send('test.json','test')
        else:
            print('Invalid choice')
            
