"""AP Monitor module to track ap status and received messages"""
import collections
import datetime
import logging
import json
from pprint import pformat
import sys
import threading
import time
import traceback
from types import *
import uuid
import weakref

import MySQLdb as mdb

from cls_logger import get_cls_logger
import ap_provision.writer as provision
from stop_thread import *
#import dispatcher

KB = 1024**1
MB = 1024**2
LOGGER = logging.getLogger(__name__)


class APMonitor(object):
    """Handles AMQP response messages from access points.

    """
    SLEEP_TIME = 45
    # TODO: Make function to determine if dispatcher still exists
    def __init__(self, dispatcher, aurora_db, host, username, password):
        self.LOGGER = get_cls_logger(self)
        # Configure dispatcher
        self.dispatcher = dispatcher
        self.dispatcher.set_timeout_callback(self.timeout)
        self.dispatcher.set_response_callback(self.process_response)
        self.dispatcher.start_connection()

        self.aurora_db = aurora_db
        # self.ut = UptimeTracker(host, username, password)
        self.poller_threads = {}

        # To handle incoming status update requests, make a command queue
        self.timeout_queue = collections.deque()
        self._make_queue_daemon()

        #Connect to Aurora mySQL Database
        self.LOGGER.info("Connecting to SQLdb...")
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
            sys.exit(1)

    def _make_queue_daemon(self):
        """Creates a queue daemon which watches for set_status calls
        and adds them to a FIFO queue.  This ensures the _set_status
        method does not get executed twice at the same time, which can
        cause the manager to place slices in a confused state.

        """
        self.LOGGER.info("Creating Queue Daemon...")
        self.qd = StoppableThread(target=self._watch_queue)
        self.qd.start()

    def _watch_queue(self, stop_event=None):
        while True:
            while len(self.timeout_queue) < 1 and not stop_event.is_set():
                time.sleep(0.1)
            if stop_event.is_set():
                self.LOGGER.info("Queue Daemon caught stop event")
                break
            (args, kwargs) = self.timeout_queue.popleft()
            self.LOGGER.debug("Queue Daemon is calling _set_status()")
            self.LOGGER.debug("args  : %s", args)
            self.LOGGER.debug("kwargs: %s", kwargs)
            self._set_status(*args, **kwargs)

    def _add_call_to_queue(self, *args, **kwargs):
        self.timeout_queue.append((args, kwargs))

    def stop(self):
        """Stops threads created by AP Monitor

        """
        self._close_all_poller_threads()
        self.qd.stop()

    def _close_all_poller_threads(self):
        self.LOGGER.debug("Closing all threads %s", self.poller_threads)
        for ap_name in self.poller_threads.keys():
            self._close_poller_thread(ap_name, 'admin')

    def _close_poller_thread(self, ap_name, unique_id):
        if ap_name in self.poller_threads and unique_id == 'admin':
            poller_thread = self.poller_threads.pop(ap_name)
            self.LOGGER.debug("Stopping thread %s %s", ap_name, poller_thread)
            poller_thread.stop()

    def process_response(self, channel, method, props, body):
        """Processes any responses it sees, checking to see if the
        correlation ID matches one sent.  If it does, the response
        is displayed along with the request originally sent.

        """
        # Basic Proof-of-Concept Implementation
        # 1. We dispatch (see method above)
        # 2. Response received: if related to a request we sent out, OK
        # ACK it
        # Update database to reflect content (i.e. success or error)

        # If we don't have a record, that means that we already
        # handled a timeout previously and something strange happened to the AP
        # to cause it to wait so long. Reset it.

        # Check if we have a record of this ID
        have_request = False
        entry = None
        self.LOGGER.info("Receiving...")
        if self.dispatcher.lock:
            self.LOGGER.info("Locked, waiting...")
            while self.dispatcher.lock:
                time.sleep(0.1)
                pass

        self.LOGGER.debug("channel: %s",channel)
        self.LOGGER.debug("method: %s", method)
        self.LOGGER.debug(repr(props))
        #self.LOGGER.debug(type(body))
        self.LOGGER.debug(json.dumps(json.loads(body), indent=4))
        self.LOGGER.debug("\nrequests_sent: %s",self.dispatcher.requests_sent)

        # Decode response
        decoded_response = json.loads(body)
        message = decoded_response['message']
        ap_name = decoded_response['ap']
        config = decoded_response['config']
        region = config['region']
        if message == 'SYN':
            #TODO: If previous message has been dispatched and we are waiting 
            #      for a response, cancel the timer and/or send the command again
            # AP has started, check if we need to restart slices
            self.LOGGER.info("%s has connected...", ap_name)
            self.aurora_db.ap_status_up(ap_name)
            self.dispatcher.remove_request(ap_syn=ap_name)
            # Tell ap monitor, let it handle restart of slices
            #self.start_poller(ap_name)
            slices_to_restart = decoded_response['slices_to_restart']
            self.restart_slices(ap_name, slices_to_restart)
            provision.update_last_known_config(ap_name, config)
            self.aurora_db.ap_update_hw_info(config['init_hardware_database'], ap_name, region)
            self.start_poller(ap_name)
            return

        elif message == 'SYN/ACK':
            self.LOGGER.info("%s responded to 'SYN' request", ap_name)
            # Cancel timers corresponding to 'SYN' message
            (have_request, entry) = self.dispatcher._have_request(props.correlation_id)
            if have_request:
                entry[1].cancel()
                self.dispatcher.requests_sent.remove(entry)
            else:
                self.LOGGER.warning("Warning: No request for received 'SYN/ACK' from %s", ap_name)
            provision.update_last_known_config(ap_name, config)
            self.aurora_db.ap_status_up(ap_name)
            self.aurora_db.ap_update_hw_info(config['init_hardware_database'], ap_name, region)

            #ap_slice_list = map(lambda slice_: slice_ in config['init_database'].keys() if slice_ != 'default_slice')
            # self.LOGGER.debug("Test map %s", test_map)
            for ap_slice_id in (ap_slice_id for ap_slice_id in config['init_database'].keys() if ap_slice_id != 'default_slice'):
                self.aurora_db.ap_slice_status_up(ap_slice_id)
            self.start_poller(ap_name)
            return


        elif message == 'FIN':
            self.LOGGER.info("%s is shutting down...", ap_name)
            try:
                self.set_status(None, None, None, False, ap_name)
                self.aurora_db.ap_update_hw_info(config['init_hardware_database'], ap_name, region)
                self.aurora_db.ap_status_down(ap_name)
                self.LOGGER.info("Updating config files...")
                provision.update_last_known_config(ap_name, config)
            except Exception as e:
                self.LOGGER.error(e.message)
            self.LOGGER.debug("Last known config:")
            self.LOGGER.debug(pformat(config))
            return

        (have_request, entry) = self.dispatcher._have_request(props.correlation_id)

        if have_request is not None:
            # decoded_response = json.loads(body)
            self.LOGGER.debug('Printing received message')
            self.LOGGER.debug(message)

            # Set status, stop timer, delete record
            #print "entry[2]:",entry[2]
            if entry[2] != 'admin':
                self.set_status(None, entry[2], decoded_response['successful'], ap_name=ap_name)
                self.aurora_db.ap_update_hw_info(config['init_hardware_database'], ap_name, region)

                self.LOGGER.info("Updating config files...")
                provision.update_last_known_config(ap_name, config)
            else:
                if message == 'AP reset':
                    self.set_status('AP reset', None, None, False, ap_name)
                    pass
                elif message == 'RESTARTING':
                    pass
                else:
                    self.set_status('slice_stats', ap_slice_stats=message["ap_slice_stats"])
                    self.aurora_db.ap_update_hw_info(config['init_hardware_database'], ap_name, region)

            self.dispatcher.remove_request(entry[0])

        else:
            self.LOGGER.info("Sending reset to '%s'", ap_name)
            # Reset the access point
            self.reset_AP(ap_name)


        # Regardless of content of message, acknowledge receipt of it
        channel.basic_ack(delivery_tag = method.delivery_tag)

    def timeout(self, ap_slice_id, ap_name, message_uuid = None):
        """This code will execute when a response is not
        received for the command associated with the unique_id
        after a certain time period.  It modifies the database
        to reflect the current status of the AP.

        """
        if message_uuid is not None:
            # dispatcher = self.dispatcher_ref()
            # if dispatcher is None:
            #     self.LOGGER.warning("Dispatcher has been deallocated")
            # else:
                # dispatcher.remove_request(message_uuid)
            self.dispatcher.remove_request(message_uuid)
        self.LOGGER.debug("%s %s", type(ap_slice_id), ap_slice_id)
        # A timeout is serious: it is likely that
        # the AP's OS has crashed, or at least aurora is
        # no longer running.
        
        #if unique_id != 'admin':
        #    self.set_status(unique_id, success=False, ap_up=False, )
        #else:
        self.set_status(None, ap_slice_id, success=False, ap_up=False, ap_name=ap_name)
        #remove thread from the thread pool
        
        #self._close_poller_thread(ap_name, ap_slice_id)

        # In the future we might do something more with the unique_id besides
        # identifying the AP, like log it to a list of commands that cause
        # AP failure, but for now it's good enough to know that our AP
        # has died and at least this command failed
        # If there are several commands waiting, this will execute several times
        # but all slices should already be marked
        # as deleted, down or failed, so there will not be any issue

    def update_records(self, message):
        """Update the traffic information of ap_slice

        :param dict message: Message containing reported slice stats

        """
        self.LOGGER.debug("Updating records...")
        for ap_slice_id in message.keys():
            try:
                self.aurora_db.ap_slice_status_up(ap_slice_id)
            except Exception:
                traceback.print_exc(file=sys.stdout)

            try:
                self.aurora_db.ap_slice_update_time_stats(ap_slice_id=ap_slice_id)
            except Exception:
                traceback.print_exc(file=sys.stdout)

            try:
                self.aurora_db.ap_slice_update_mb_sent(ap_slice_id, float(message.get(ap_slice_id))/MB)
            except Exception:
                traceback.print_exc(file=sys.stdout)
            
    def set_status(self, cmd_category, *args, **kwargs):
        """This function's arguments used to look like 
            unique_id, success, ap_up=True, ap_name=None

        """
        self.LOGGER.debug("Adding set_status call to queue for (%s, %s)", args, kwargs)
        self._add_call_to_queue(cmd_category, *args, **kwargs)

    def _set_status(self, cmd_category, *args, **kwargs):
        """Sets the status of the associated request in the
        database based on the previous status, i.e. pending -> active if
        create slice, deleting -> deleted if deleting a slice, etc.
        If the ap_up variable is false, the access point
        is considered to be offline and in an unknown state,
        so *all* slices are marked as such (down, failed, etc.).

        """
        if cmd_category is None:
            self._set_status_standard(*args, **kwargs)
        elif cmd_category is 'AP reset':
            self._set_status_standard(*args, **kwargs)
        elif cmd_category is 'slice_stats':
            self._set_status_stats(*args, **kwargs)

        return True

    def _set_status_stats(self, ap_slice_stats=None):
        try:
            self.update_records(ap_slice_stats)
        except:
            traceback.print_exc(file=sys.stdout)

    def _set_status_standard(self, unique_id, success, ap_up=True, ap_name=None):
        # DEBUG
        if unique_id != 'SYN' and unique_id is not None:
            self.LOGGER.info("Updating ap status for ID %s.", str(unique_id))
        else:
            self.LOGGER.info("Updating ap status for ID %s.", str(ap_name))
        self.LOGGER.info("Request successful: %s", str(success))
        self.LOGGER.info("Access Point up: %s", str(ap_up))
        # Code:
        # Identify slice by unique_id
        # if ap_up:
        #   if pending and success, mark active
        #   else if deleting and success, mark deleted
        #   else if pending and failed, mark failed
        #   else if deleting and failed, mark failed (forcing user
        # to try deleting again or contact admin saying I can't delete;
        # this situation is so unlikely that if it happens an admin
        # really should come by and see what's going on)
        # else :
        # for all slices and/or commands relating to AP:
        #   if slice is active, mark down
        #   else if slice is deleting, mark deleted (will be when we reinitialize)
        #   else if slice is pending, mark failed
        try:
            # Access point is up - we are receiving individual packets
            if ap_up:
                self.aurora_db.ap_status_up(ap_name)
                self.aurora_db.ap_up_slice_status_update(unique_id, ap_name, success)
                self.aurora_db.ap_slice_update_time_stats(ap_slice_id=unique_id)
            # Access point down, mark all slices and failed/down
            else:
                if ap_name is None:
                    ap_name = self.aurora_db.get_wslice_physical_ap(ap_slice_id)
                self.aurora_db.ap_slice_update_time_stats(ap_name=ap_name)
                self.aurora_db.ap_status_down(ap_name)
                self.aurora_db.ap_down_slice_status_update(ap_name)
                self._close_poller_thread(ap_name, 'admin')

        except Exception, e:
            self.LOGGER.error(str(e))

    def restart_slices(self, ap, slice_list):
        """Restarts the slices on their access point.

        :param str ap: Name of the access point
        :param list slice_list: List of slices to restart

        """
        try:
            for ap_slice_id in slice_list:
                user_id = self.aurora_db.get_user_for_active_ap_slice(ap_slice_id)
                self.LOGGER.debug("Returned user id %s", user_id)
                if user_id is not None:
                    assert type(user_id) is IntType,"Need user_id to be IntType"
                    self.LOGGER.info("%s for tenant %s", ap_slice_id, user_id)
                    self.LOGGER.info("Restarting %s", ap_slice_id)
                    self.dispatcher.dispatch({'slice': ap_slice_id,
                                              'command': 'restart_slice',
                                              'user': user_id
                                             },
                                             ap)
                else:
                    self.LOGGER.warn("No active slice %s", slice_id)
        except Exception, e:
            traceback.print_exc(file=sys.stdout)

    def start_poller(self, ap_name):
        """Starts a poller to track the status of an access point.

        :param str ap_name: Name of the access point

        """
        #poller_thread = thread(ThreadClass, self)
        poller_thread = TimerThread(target=self.poll_AP, args=(ap_name,))
        self.LOGGER.debug("Starting poller on thread %s", poller_thread)
        self.poller_threads[ap_name] = poller_thread
        poller_thread.start()

    def poll_AP(self, ap_name, stop_event=None):
        """Poller thread target: sends the access point a message in a 
        regular interval.

        :param str ap_name: Name of the access point

        """
        #print "Timeout from Dispatcher", self.dispatcher.TIMEOUT
        own_thread = self.poller_threads[ap_name]
        while ap_name in self.poller_threads:
            #time.sleep(APMonitor.SLEEP_TIME)
            self.LOGGER.debug("%s thread is %s", ap_name, own_thread)
            self.get_stats(ap_name)
            # dispatcher = self.dispatcher_ref()
            for i in range(self.dispatcher.TIMEOUT + 5):
                if stop_event.is_set():
                    self.LOGGER.debug("Caught stop event for %s", own_thread)
                    break
                time.sleep(1)
            if stop_event.is_set():
                self.LOGGER.debug("Poller thread for %s is dying now" % ap_name)
                break

    def reset_AP(self, ap):
        """Reset the access point.  If there are serious issues, however,
        a restart may be required.

        """
        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'reset' } , ap)

    def restart_AP(self, ap):
        """Restart the access point, telling the OS to reboot.

        """
        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'restart' } , ap)

    def get_stats(self, ap):
        """Query the access point for slice stats."""
        # The unique ID is fixed to be all F's
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'get_stats'}, ap)


#for test
#if __name__ == '__main__':
#    host = 'localhost'
#    mysql_username = 'root'
#    mysql_password = 'supersecret'
#    manager = APMonitor(None, host , mysql_username, mysql_password)
#    manager.set_status(12, True)
