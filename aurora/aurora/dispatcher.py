# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith &
#              Mike Kobierski 
#
"""The dispatcher module handles AMQP connection setup and transmission 
of messages.

"""
import json
import logging
from pprint import pprint, pformat
import signal
import sys
import threading
import traceback
import time
import uuid
import weakref

import pika

from aurora.cls_logger import get_cls_logger
from aurora.ap_provision import writer as provision
from aurora.stop_thread import *
from aurora.exc import *

PIKA_LOGGER = logging.getLogger('pika')
PIKA_LOGGER.setLevel(logging.INFO)
LOGGER = logging.getLogger(__name__)


class Dispatcher(object):
    """The Dispatcher class sets up a connection to a RabbitMQ server
    and configures a reply queue for access points to direct messages
    to.  It also provides a method for sending a configuration message 
    to a specific access point.

    """
    lock = []
    TIMEOUT = 45
    RESTART_TIMEOUT = 30
    WAIT_TO_DISPATCH_TIMEOUT = 5
    SPLIT_SECOND = 1
    WAIT_TIME_INTERVAL = 0.25

    dispatch_count = 0
    status_closing = False

    def __init__(self, host, username, password, mysql_username, 
                 mysql_password, aurora_db, queue=''):
        """Configures a dispatcher instance in order to set up 
        connections, channels, and queues.

        """
        self.LOGGER = get_cls_logger(self)
        self.LOGGER.info("Constructing Dispatcher...")
        # Run Pika logger so that error messages get printed
        
        self.host = host
        self.username = username
        self.password = password
        Dispatcher.lock = []
        self.restarting_connection = False
        self.aurora_db = aurora_db
        self.timeout_callback = None
        self.response_callback = None
        self.close_pollers_callback = None
        self.queue = queue

        # Create list for requests sent out
        self.requests_sent = []


    def __del__(self):
        self.LOGGER.info("Deconstructing...")

    def set_timeout_callback(self, timeout_callback):
        """Stores a callback function which will be called if a 
        sent message does not receive a correlated reply within 
        a set timeout.

        :param callable timeout_callback: 

        """
        self.timeout_callback = timeout_callback

    def set_response_callback(self, response_callback):
        """Stores a method which will be executed upon receipt of a 
        message on an incoming queue.

        :param callable response_callback:

        """
        self.response_callback = response_callback

    def set_close_pollers_callback(self, close_pollers_callback):
        """Stores a method which will close all AP pollers (see 
        :func:`close_all_poller_threads \
            <aurora.ap_monitor.APMonitor.close_all_poller_threads>`) in 
        case the connection dies and needs to be restarted.

        :param callable close_pollers_callback:

        """
        self.close_pollers_callback = close_pollers_callback

    def start_connection(self):
        """External interface for starting a new AMQP connection."""
        self._start_connection()

    def _start_connection(self):
        """Step 1: Entry point for starting a new AMQP connetion.

        Connects to RabbitMQ server and provides a callback to execute 
        once the connection is established.  Begins an IOLoop to watch 
        for message events.

        """
        self.channel = None
        self.connection = None
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.SelectConnection(
            pika.ConnectionParameters(
                host=self.host,
                credentials=credentials
            ),
            self.on_connected)

        # Start ioloop, this will quit by itself when 
        # Dispatcher().stop() is run
        self.listener = threading.Thread(
            target=self.ioloop_thread_start_target)
        self.LOGGER.info("Starting pika listener %s", self.listener)
        self.listener.start()

    def on_connected(self, connection):
        """Step 2: Requests a new channel and provides a callback which 
        will execute once a channel has been assigned.

        :param connection:
        :type connection: 
            :class:`pika.adapters.select_connection.SelectConnection` 

        """
        self.connection.channel(self.channel_open)

    def channel_open(self, new_channel):
        """Step 3: Store the returned channel and request a reply 
        queue to which access points can send their messages.

        :param pika.channel.Channel new_channel:

        """
        self.channel = new_channel
        Dispatcher.status_closing = False

        response = self.channel.queue_declare(auto_delete=True,
                                              queue=self.queue,
                                              callback=self.on_queue_declared)
        # Commented Apr 9, replace if problems exist without durable
        # option.
        # response = self.channel.queue_declare(durable=True, 
        #                                       callback=self.on_queue_declared)

    def on_queue_declared(self, frame):
        """Step 4: Store the returned reply queue and track it for 
        future reference by access points in AP provision database.

        :param pika.frame.Method frame:

        """
        self.callback_queue = frame.method.queue
        provision.update_reply_queue(self.callback_queue)
        self.consume_on_queue(self.callback_queue)

    def consume_on_queue(self, queue):
        """Step 5: Direct all incoming messages to be handled by 
        :func:`set_response_callback`.

        Check whether we were restarting a connection - if so, set the 
        restarting flag to false - the connection is now active.
        In the case it isn't being restarted, send let access points 
        know manager has successfully set up a connection, channel, and
        reply queue (send manager 'SYN' message).

        Also launch a thread to monitor the status of the AMQP 
        connection.

        :param str queue: The queue to which access points will respond

        """
        self.channel.basic_consume(self.response_callback,
                                   queue=queue)
        if self.restarting_connection:
            self.restarting_connection = False
        else:
            self._start_pika_channel_open_monitor()
            self._send_manager_up_status()

    def ioloop_thread_start_target(self):
        """A target method for a thread in which pika's IOLoop can run.
        Since some exceptions can happen in the IOLoop thread, catch 
        them if they occur and restart the connection to start with 
        a clean slate.

        """
        if self.connection is None:
            return
        try:
            self.connection.ioloop.start()
        except IndexError as e:
            # Something bad happened, likely "pop from an empty deque"
            # This will cause the ioloop poller to die, and all further
            # messages sent by the AP will no longer be received.  The
            # result is that a timeout will occur on a sent message,
            # and the AP will be marked as 'DOWN'.
            self.LOGGER.warn(e.message)
            self._restart_connection()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self._restart_connection()
        self.LOGGER.info("IOLoop is dying")

    def stop(self):
        """External interface for stopping the dispatcher.  This will
        cleanly let RabbitMQ know we're closing up, and will also 
        stop the pika channel monitor thread.

        """
        self._stop_pika_channel_open_monitor()
        self._stop_connection()

        del self.connection
        del self.listener
        del self.timeout_callback
        del self.response_callback
        del self.close_pollers_callback

    def _stop_connection(self):
        """Runs cleanup to stop the dispatcher's connection with 
        RabbitMQ.  

        Stops the poller threads created in AP Monitor so 
        they will not try and send a message while the connection is 
        down. Also stops the timers associated with sent messages - 
        if we cannot receive a reply it doesn't make sense to wait for 
        one.

        """
        self.close_pollers_callback()
        self.LOGGER.info("Stopping all request timers")
        self._stop_all_request_sent_timers()
        try:
            del self.channel 
            self.LOGGER.warn("Connection state: %s",
                             self.connection.connection_state)
            Dispatcher.status_closing = True
            self.connection.close()
            Dispatcher.lock = []
        except AttributeError as e:
            self.LOGGER.debug("Connection already closed...")
            

    def _restart_connection(self):
        """A method to stop and start a connection, waiting for some 
        timeout for a connection to be established and a channel to 
        be created.  

        Once a connection and channel have been set up, this method 
        notifies APs (sends 'SYN' message).

        """
        self.LOGGER.info("Channel has died, restarting...")
        self._stop_connection()
        self.listener.join()

        # Dispatcher.lock = []
        printed_waiting = False
        self.LOGGER.info("Waiting for channel to close...")
        while True:
            try:
                if self.connection.is_closed or self.connection.is_closing:
                    self.LOGGER.debug("Connection closed...")
                    break
            except AttributeError as e:
                self.LOGGER.debug("Connection closed (doesn't exist)...")
                break
            time.sleep(1)

        self.restarting_connection = True
        self.LOGGER.info("Starting new connection...")
        self._start_connection()
        timeout_to_restart = self.RESTART_TIMEOUT
        self.LOGGER.info("Waiting for channel to open...")
        while True:
            try:
                if self.connection.is_open and self.channel.is_open:
                    break
            except AttributeError as e:
                self.LOGGER.warn("No channel: %s", e.message)
                pass
            # Channel is not up again yet
            time.sleep(1)
            if timeout_to_restart == 0:
                # Wait 30 seconds for a restart, otherwise try again
                return self._restart_connection()
            timeout_to_restart -= 1
        self.LOGGER.info("Channel back up...")
        self._send_manager_up_status()

    def _stop_all_request_sent_timers(self):
        """Empties the list tracking sent requests, and cancels all 
        associated timers.

        """
        while self.requests_sent:
            entry = self.requests_sent.pop()
            self.LOGGER.info("Cancelling timer %s", entry[1])
            entry[1].cancel()

    def _send_manager_up_status(self):
        """Dispatches a 'SYN' message to all known access points.  If 
        the access points respond, they are marked as 'UP', otherwise, 
        after some timeout, they will be marked as 'DOWN'.

        """
        self.aurora_db.ap_status_unknown()
        for ap in self.aurora_db.get_ap_list():
            try:
                self.dispatch({'command':'SYN'}, ap)
            except AuroraException as e:
                self.LOGGER.warn(e.message)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)

    def _start_pika_channel_open_monitor(self):
        """Creates a thread which will monitor the pika connection.  

        The thread is stoppable, and will run an endless loop until its 
        stop_event is set.

        """
        self._pika_monitor_thread = StoppableThread(
            target=self._pika_monitor_loop)
        self.LOGGER.info("Starting pika monitor thread %s", 
                         self._pika_monitor_thread)
        self._pika_monitor_thread.start()

    def _stop_pika_channel_open_monitor(self):
        """Stops the pika monitor thread."""
        self.LOGGER.info("Stopping pika monitor thread %s", 
                         self._pika_monitor_thread)
        self._pika_monitor_thread.stop()
        self._pika_monitor_thread.join()

    def _pika_monitor_loop(self, stop_event=None):
        """Target for pika monitor thread.

        Runs a continuous loop until stop_event is set, testing whether 
        pika connection is active and a channel exists.  If something 
        has gone wrong, :func:`_restart_connection()` is called.

        :param stop_event:
        :type stop_event: :class:`threading.Event`

        """
        while not stop_event.is_set():
            do_reset = False
            try:
                if not (self.connection.is_open and self.channel.is_open):
                    self.LOGGER.warn("Pika connection down, restarting")
                    do_reset = True
            except AttributeError:
                self.LOGGER.warn("Connection doesn't exist, restarting")
                do_reset = True
            if do_reset:
                self._restart_connection()
                self.LOGGER.warn("Continuing pika_monitor loop")

            time.sleep(0.5)

    def dispatch(self, config, ap, unique_id=None):
        """Send data to the specified queue.

        Some commands will provide a unique_id to use, such as 
        :func:`ap_slice_create` -- the ap_slice_id will typically be used.  
        In the case that none is provided, one will be generated.  
        For both cases, the unique_id is prepended by the access point 
        name, in order to identify which messages have been sent to 
        which APs.

        Some issues occur if this method is called many times in 
        parallel for the same AP, thus a access-point dependent lock 
        is used. Everything should be OK when dispatching in parallel 
        to many different APs.

        .. note::

            This issue also happens when sending and receiving for 
            the same AP in parallel, thus when the messages are 
            received by the callable in ``self.response_callback``, 
            this lock should be checked::

                if ap_name in Dispatcher.lock:
                    LOGGER.info("Locked for %s, waiting...", ap_name)
                    while ap_name in Dispatcher.lock:
                        time.sleep(0.1)

        .. note::

            The caller is expected to set SQL database properties such 
            as status.

        :param dict config: Slice configuration
        :param str ap: Access point on which slice should be created 
        :param str unique_id: Unique ID to be assigned as the AMQP
                              correlation ID
        :raises: 
            :exc:`DispatchLockedForAPTimeout \
                <aurora.exc.DispatchLockedForAPTimeout>`\n
            :exc:`MessageSendAttemptWhileClosing \
                <aurora.exc.MessageSendAttemptWhileClosing>`\n
            :exc:`DispatchWaitForOpenChannelTimeout \
                <aurora.exc.DispatchWaitForOpenChannelTimeout>`\n
            :exc:`KeyboardInterrupt`\n

        """

        # Create unique_id if none exists
        if unique_id is None:
            unique_id = "%s-%s" % (ap, str(uuid.uuid4()))
        else:
            unique_id = "%s-%s" % (ap, unique_id)

        # Convert JSON to string
        message = json.dumps(config)
        self.LOGGER.debug(message)

        # Send JSON
        # We attach a reply_to and correlation ID to tell the AP to send 
        # a message to the queue we create (randomly generated name) at 
        # init with the correlation id specified.  This means that we 
        # can see if our request executed successfully or not 
        # See http://www.rabbitmq.com/tutorials/tutorial-six-python.html 
        # for more info
        
        # Errors happen if too many people try and publish and receive
        # at the same time, thus a primitive lock for each access
        # point is used.  The lock contains a list of access point
        # names which are currently being dispatched to.  If another
        # dispatch call is running, the list will have a non-zero
        # length, but as long as we are not dispatching to the same
        # access point we can continue.
        wait_timer = 0
        if ap in Dispatcher.lock:
            self.LOGGER.info("Locked for %s, waiting...", ap)
            wait_timer = 0
            while ap in Dispatcher.lock:
                if wait_timer > self.WAIT_TO_DISPATCH_TIMEOUT:
                    raise DispatchLockedForAPTimeout(ap=ap)
                wait_timer += self.WAIT_TIME_INTERVAL
                time.sleep(self.WAIT_TIME_INTERVAL)

        # For safety, in the case that another call to this method is 
        # already executing, delay by a split second.
        

        if Dispatcher.status_closing:
            raise MessageSendAttemptWhileClosing()

        self.LOGGER.debug("Locking for %s...", ap)
        Dispatcher.lock.append(ap)

        current_dispatch_calls = len(Dispatcher.lock) - 1
        if current_dispatch_calls > 0:
            # If others are using method, wait for some variable amount
            # of time, dependent on how many others are using it.
            time.sleep(self.SPLIT_SECOND*current_dispatch_calls)

        # Dispatch, catch if no channel exists
        wait_timer = 0
        while True:
            if wait_timer > self.WAIT_TO_DISPATCH_TIMEOUT:
                raise DispatchWaitForOpenChannelTimeout()
            try:
                if self.connection.is_open and self.channel.is_open:
                    break
            except AttributeError:
                pass
            wait_timer += self.WAIT_TIME_INTERVAL
            time.sleep(self.WAIT_TIME_INTERVAL)
        die_by_kb = False
        try:
            self.channel.basic_publish(
                exchange='', 
                routing_key=ap, 
                body=message, 
                properties=pika.BasicProperties(
                    reply_to = self.callback_queue, 
                    correlation_id = unique_id, 
                    content_type="application/json"
                )
            )
        except IndexError as e:
            # Likely publishing the message didn't work
            self.LOGGER.warn(e.message)
            try:
                # Force the channel to close, the channel monitor should
                # notice, and restart the channel
                self.LOGGER.info("Forcing a channel close")
                self._stop_connection()
            except Exception:
                traceback.print_exc(file=sys.stdout)
        except KeyboardInterrupt:
            die_by_kb = True
        except Exception as e:
            # A more serious error occured
            traceback.print_exc(file=sys.stdout)
            #self.LOGGER.error(e.message)
        else:
            self.LOGGER.info("Message for %s dispatched", ap)
            ap_slice_id = 'NONE'
            if config['command'] == 'SYN':
                ap_slice_id = 'SYN'
            else:
                ap_slice_id = config['slice']
            # Start a timeout countdown
            self.LOGGER.debug("ap_slice_id %s",ap_slice_id)
            
            try:
                timer = threading.Timer(self.TIMEOUT, 
                                        self.timeout_callback, 
                                        args=(ap_slice_id,ap,unique_id))
            except AttributeError as e:
                # Likely tried to start a timer while shutting down
                # resulting in non-existance of timeout_callback 
                self.LOGGER.warn(e.message)

            self.LOGGER.debug("Adding timer %s", timer)
            self.requests_sent.append((unique_id, timer, ap_slice_id))
            timer.start()
            self.LOGGER.debug("requests_sent %s",self.requests_sent)
            if len(self.requests_sent) > 0:
                self.LOGGER.debug("Starting timer: %s",self.requests_sent[-1])
            else:
                self.LOGGER.error("Cannot start nonexistant timer")

        self.LOGGER.debug("Unlocking for %s...", ap)
        try:
            Dispatcher.lock.remove(ap)
        except ValueError as e:
            self.LOGGER.warn("Tried to remove nonexistant ap_name from lock")
        if die_by_kb:
            raise KeyboardInterrupt()

    def get_open_channel(self):
        """Returns ``self.channel`` if it is open, otherwise 
        returns ``None``.

        """
        if self.channel.is_open:
            return self.channel
        return None

    def _get_uuid_for_ap_syn(self, ap_syn):
        """A factory for finding all messages by UUID sent to the 
        access point name ``ap_syn``.

        :param str ap_syn: Name of the access point for which messages 
                           should be found.
        :yields: List of message UUIDs for messages sent to AP

        """
        for request in self.requests_sent:
            if request[0].startswith(ap_syn + '-'):
                yield request[0]

    def have_request(self, correlation_id):
        """Checks whether a request for ``correlation_id`` was 
        previously sent.  If it was, returns a tuple containing a bool
        for success and the request, if exists, else ``None``.

        :param str correlation_id: Correlation ID to check
        :returns: tuple -- Index 0 is true if request exists, 
                  index 1 contains the request or ``None``.

        """
        for request in self.requests_sent:
            if request[0] == correlation_id:
                return (True, request)
        return (False, None)

    def remove_request(self, message_uuid=None, ap_syn=None):
        """Removes a request from the requests sent list and cancels 
        the associated timer.  If ap_syn is set, all requests for that 
        AP are removed and their timers cancelled -- at this point it 
        is known that the AP will not respond to any of the previously 
        issued messages.

        :param str message_uuid: UUID of the request to remove 
        :param str ap_syn: Name of the AP from which Manager received 
                           a syn message

        """
        # If ap_syn isn't None, find all requests for this ap and 
        # cancel them to create a clean slate.  User will have to 
        # manually restart failed slices. 
        if ap_syn:
            for message_uuid in self._get_uuid_for_ap_syn(ap_syn):
                (have_request, request) = self.have_request(message_uuid)
                if have_request:
                    self.LOGGER.debug("Cancelling timer %s", request[1])
                    request[1].cancel()
                    self.LOGGER.debug("Removing request %s", str(request))
                    self.requests_sent.remove(request)
        else:
            (have_request, request) = self.have_request(message_uuid)
            if have_request:
                self.LOGGER.debug("Cancelling timer %s", request[1])
                request[1].cancel()
                self.LOGGER.debug("Removing request %s", str(request))
                self.requests_sent.remove(request)


# Menu loop; thanks Kevin
# Obviously this code will not be in a final version
def main():
    #######
    #  WARNING! (Apr 9, 2014)
    #
    #  THIS BOILERPLATE SCRIPT IS OUTDATED AND IS NOT 
    #  GUARANTEED TO WORK!

    print "Warning: Executing untested code in dispatcher.main()"

    exitLoop = False

    import config

    ######
    # Connection Variables
    host = config.CONFIG['dispatcher']['host']
    username = config.CONFIG['dispatcher']['username']
    password = config.CONFIG['dispatcher']['password']
    mysql_username = config.CONFIG['mysql']['mysql_username']
    mysql_password = config.CONFIG['mysql']['mysql_username']
    sender = Dispatcher(host, username, password, 
                        mysql_username, mysql_password)

    import ap_provision.http_srv as provision_srv
    provision_srv.run()

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
                config = json.load(file)
                file.close()
            except:
                print('Bad file, returning to menu')
            else:

                print('Enter ap ID')
                ap = raw_input()
                print('Enter unique id')
                unique_id = raw_input()
                sender.dispatch( config, ap, unique_id)

    provision_srv.stop()

if __name__ == '__main__':
    main()
    