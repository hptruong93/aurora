import atexit
import collections
import logging
import sys
import threading
import time
import uuid
import weakref

import MySQLdb as mdb

from cls_logger import get_cls_logger

LOGGER = logging.getLogger(__name__)


class APMonitor(object):

    sql_locked = None
    SLEEP_TIME = 45
    # TODO: Make function to determine if dispatcher still exists
    def __init__(self, dispatcher, host, username, password):
        self.LOGGER = get_cls_logger(self)
        self.dispatcher_ref = weakref.ref(dispatcher)
        self.LOGGER.debug("Made weak ref %s %s",self.dispatcher_ref, self.dispatcher_ref())

        self.aurora_db = self.dispatcher_ref().aurora_db
        self.ut = UptimeTracker(host, username, password)
        self.poller_threads = {}

        # To handle incoming status update requests, make a command queue
        self.timeout_queue = collections.deque()
        self._make_queue_daemon()

        #Connect to Aurora mySQL Database
        self.LOGGER.info("Connecting to SQLdb...")
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
            APMonitor.sql_locked = False
        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s" % (e.args[0], e.args[1]))
            sys.exit(1)

        atexit.register(self._closeSQL)

    def _closeSQL(self):
        self.LOGGER.info("Closing SQL connection...")
        self.aurora_db.ap_status_unknown()
        if self.con:
            self.con.close()
        else:
            self.LOGGER.info('Connection already closed!')

    def _make_queue_daemon(self):
        self.LOGGER.info("Creating Queue Daemon...")
        self.qd = StoppableThread(target=self._watch_queue)
        self.qd.start()

    def _watch_queue(self, stop_event=None):
        while True:
            while len(self.timeout_queue) < 1 and not stop_event.is_set():
                time.sleep(1)
            if stop_event.is_set():
                self.LOGGER.info("Queue Daemon caught stop event")
                break
            (args, kwargs) = self.timeout_queue.popleft()
            self._set_status(*args, **kwargs)

    def _add_call_to_queue(self, *args, **kwargs):
        self.timeout_queue.append((args, kwargs))

    def stop(self):
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

    def timeout(self, ap_slice_id, ap_name, message_uuid = None):
        """This code will execute when a response is not
        received for the command associated with the unique_id
        after a certain time period.  It modifies the database
        to reflect the current status of the AP."""

        if message_uuid is not None:
            dispatcher = self.dispatcher_ref()
            if dispatcher is None:
                self.LOGGER.warning("Dispatcher has been deallocated")
            else:
                dispatcher.remove_request(message_uuid)
        self.LOGGER.debug("%s %s", type(ap_slice_id), ap_slice_id)
        # A timeout is serious: it is likely that
        # the AP's OS has crashed, or at least aurora is
        # no longer running.
        
        #if unique_id != 'admin':
        #    self.set_status(unique_id, success=False, ap_up=False, )
        #else:
        self._add_call_to_queue(ap_slice_id, success=False, ap_up=False, ap_name=ap_name)
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
        """Update the traffic information of ap_slice"""
        self.ut.update_traffic(message)

    def set_status(self, unique_id, success, ap_up=True, ap_name=None):
        self._add_call_to_queue(unique_id, success, ap_up, ap_name)

    def _set_status(self, unique_id, success, ap_up=True, ap_name=None):
        """Sets the status of the associated request in the
        database based on the previous status, i.e. pending -> active if
        create slice, deleting -> deleted if deleting a slice, etc.
        If the ap_up variable is false, the access point
        is considered to be offline and in an unknown state,
        so *all* slices are marked as such (down, failed, etc.)."""

        # DEBUG
        if unique_id != 'SYN':
            self.LOGGER.info("Updating ap status for ID %s.", str(unique_id))
        else:
            self.LOGGER.info("Updating ap status for ID %s.", str(ap_name))
        self.LOGGER.info("Request successful: %s", str(success))
        self.LOGGER.info("Access Point up: %s", str(ap_up))

        if APMonitor.sql_locked:
            self.LOGGER.info("SQL Access is locked, waiting...")
            while APMonitor.sql_locked:
                time.sleep(0.1)
                pass
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
            with self.con:
                APMonitor.sql_locked = True
                cur = self.con.cursor()

                # Access point is up - we are receiving individual packets
                if ap_up:
                    self.aurora_db.ap_status_up(ap_name)
                    # Get status
                    cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                    status = cur.fetchone()
                    if status:
                        status = status[0]
                    else:
                        raise Exception("No status for ap_slice_id %s\n" % unique_id)
                    # Update status
                    if status == 'PENDING':
                        if success:
                            cur.execute("UPDATE ap_slice SET status='ACTIVE' WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                        else:
                            cur.execute("UPDATE ap_slice SET status='FAILED' WHERE ap_slice_id=\'"+str(unique_id)+"\'")

                    elif status == 'DELETING':
                        if success:
                            cur.execute("UPDATE ap_slice SET status='DELETED' WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                        else:
                            cur.execute("UPDATE ap_slice SET status='FAILED' WHERE ap_slice_id=\'"+str(unique_id)+"\'")

                    elif status == 'DOWN':
                        if success:
                            cur.execute("UPDATE ap_slice SET status='ACTIVE' WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                        else:
                            cur.execute("UPDATE ap_slice SET status='FAILED' WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                    else:
                        self.LOGGER.info("Unknown Status, ignoring...")

                # Access point down, mark all slices and failed/down
                else:
                    if ap_name:
                        physical_ap = ap_name
                    else:
                        to_execute = "SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'"
                        self.LOGGER.debug(to_execute)
                        cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                        physical_ap = cur.fetchone()
                        if physical_ap:
                            physical_ap = physical_ap[0]
                        else:
                            raise Exception("Cannot fetch physical_ap for slice %s\n" % unique_id)

                    self.LOGGER.debug("physical_ap: %s", physical_ap)
                    self.aurora_db.ap_status_down(physical_ap)
                    self._close_poller_thread(physical_ap, 'admin')
                    #Get all slices associated with this ap
                    cur.execute("SELECT ap_slice_id FROM ap_slice WHERE physical_ap=\'"+str(physical_ap)+"\' AND status<>'DELETED'")

                    #Prune List of ap_slice_id
                    raw_list = cur.fetchall()
                    if raw_list:
                        slice_list = []
                        for entry in raw_list:
                            slice_list.append(entry[0])
                    else:
                        raise Exception("No slices on physical_ap '%s'\n" % physical_ap)

                    self.LOGGER.debug("raw_list: %s",raw_list)
                    self.LOGGER.debug("slice_list: %s",slice_list)

                    for entry in slice_list:
                        #Get status
                        cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=\'"+str(entry)+"\'")
                        status = cur.fetchone()
                        if status:
                            status = status[0]
                        else:
                            raise Exception("No status for ap_slice_id %s\n" % unique_id)

                        # Update status
                        if status == 'ACTIVE':
                            cur.execute("UPDATE ap_slice SET status='DOWN' WHERE ap_slice_id=\'"+str(entry)+"\'")
                            self.LOGGER.info("%s: %s - Updated to status: 'DOWN'", entry, status)
                        elif status == 'DELETING':
                            cur.execute("UPDATE ap_slice SET status='DELETED' WHERE ap_slice_id=\'"+str(entry)+"\'")
                            self.LOGGER.info("%s: %s - Updated to status: 'DELETED'", entry, status)
                        elif status == 'PENDING':
                            cur.execute("UPDATE ap_slice SET status='FAILED' WHERE ap_slice_id=\'"+str(entry)+"\'")
                            self.LOGGER.info("%s: %s - Updated to status: 'FAILED'", entry, status)
                        else:
                            self.LOGGER.info("%s: %s - Unknown Status, ignoring...", entry, status)

        except Exception, e:
            self.LOGGER.error(str(e))
        finally:
            APMonitor.sql_locked = False
        self.ut.update_status(unique_id, ap_up, ap_name)
        return True

    def restart_slices(self, ap, slice_list):
        if APMonitor.sql_locked:
            self.LOGGER.info("SQL Access is locked, waiting...")
            while APMonitor.sql_locked:
                time.sleep(0.1)
                pass
        try:
            with self.con:
                APMonitor.sql_locked = True
                cur = self.con.cursor()
                for slice_id in slice_list:
                    self.LOGGER.info("Restarting %s", slice_id)
                    cur.execute("SELECT status, tenant_id FROM ap_slice WHERE ap_slice_id = '%s'" %
                                slice_id)
                    items = cur.fetchone()
                    if items:
                        status = items[0]
                        user_id = items[1]
                        self.LOGGER.info("%s %s for tenant %s", (slice_id, status, user_id))
                    else:
                        raise Exception("No slice %s\n" % slice_id)
                    if status != 'DELETED' and status != 'DELETING':
                        # Restart slice as it wasn't deleted since AP went down
                        dispatcher = self.dispatcher_ref()
                        dispatcher.dispatch({'slice': slice_id,
                                             'command': 'restart_slice',
                                             'user': user_id},
                                             ap)
        except Exception, e:
            self.LOGGER.error("Error %s", e)
        finally:
            APMonitor.sql_locked = False

    def start_poller(self, ap_name):
        
        #poller_thread = thread(ThreadClass, self)
        poller_thread = TimerThread(target=self.poll_AP, args=(ap_name,))
        self.LOGGER.debug("Starting poller on thread %s", poller_thread)
        self.poller_threads[ap_name] = poller_thread
        poller_thread.start()

    def poll_AP(self, ap_name, stop_event=None):
        #print "Timeout from Dispatcher", self.dispatcher.TIMEOUT
        own_thread = self.poller_threads[ap_name]
        while ap_name in self.poller_threads:
            #time.sleep(APMonitor.SLEEP_TIME)
            self.LOGGER.debug("%s thread is %s", ap_name, own_thread)
            self.get_stats(ap_name)
            dispatcher = self.dispatcher_ref()
            for i in range(dispatcher.TIMEOUT + 5):
                if stop_event.is_set():
                    self.LOGGER.debug("Caught stop event for %s", own_thread)
                    break
                time.sleep(1)
            if stop_event.is_set():
                self.LOGGER.debug("Poller thread for %s is dying now" % ap_name)
                break

    def reset_AP(self, ap):
        """Reset the access point.  If there are serious issues, however,
        a restart may be required."""

        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher_ref().dispatch( { 'slice' : 'admin', 'command' : 'reset' } , ap)

    def restart_AP(self, ap):
        """Restart the access point, telling the OS to reboot."""

        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher_ref().dispatch( { 'slice' : 'admin', 'command' : 'restart' } , ap)

    def get_stats(self, ap):
        """Update the access point """

        # The unique ID is fixed to be all F's
        self.dispatcher_ref().dispatch( { 'slice' : 'admin', 'command' : 'get_stats'}, ap)

class UptimeTracker(object):
    def __init__(self, host, username, password):
        self.LOGGER = get_cls_logger(self)
        #Connect to Aurora mySQL Database
        self.LOGGER.info("Connecting to SQLdb...")
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
        except mdb.Error, e:
            self.LOGGER.error("Error %d: %s", e.args[0], e.args[1])
            sys.exit(1)

        atexit.register(self.closeSQL)

    def closeSQL(self):
        self.LOGGER.info("Closing SQL connection...")
        if self.con:
            self.con.close()
        else:
            self.LOGGER.warning('Connection already closed!')

    def update_traffic(self, message):
        try:
            with self.con:
                cur = self.con.cursor()
                for ap_slice in message.keys():
                    cur.execute("UPDATE ap_slice_status SET\
                                bytes_sent=%s WHERE ap_slice_id='%s'"
                                % (str(message.get(ap_slice)), ap_slice))
        except Exception, e:
            self.LOGGER.error("Error: %s", str(e))

    def update_status(self, unique_id, ap_up=True, ap_name=None):
        #Access Point is up update the ap_slice
        if ap_up and unique_id != 'admin':
            self.update_apslice(unique_id)
        #Access Point down fetch all ap_slice and update them
        else:
            try:
                with self.con:
                    cur = self.con.cursor()
                    if ap_name:
                        physical_ap = ap_name
                    else:
                        cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=%s", str(unique_id))
                        physical_ap = cur.fetchone()
                        if physical_ap:
                            physical_ap = physical_ap[0]
                        else:
                            raise Exception("Cannot fetch physical_ap for slice=%s\n" % unique_id)
                    #Get all slices associated with this ap
                    cur.execute("SELECT ap_slice_id FROM ap_slice WHERE physical_ap=%s", str(physical_ap))
                    raw_list = cur.fetchall()
                    if raw_list:
                        slice_list = []
                        for entry in raw_list:
                            slice_list.append(entry[0])
                    else:
                        raise Exception("No slices on physical_ap '%s'\n" % physical_ap)
                    for entry in slice_list:
                        self.update_apslice(entry)
            except Exception, e:
                self.LOGGER.error("Error: %s", str(e))

    def update_apslice(self, unique_id):
        #TODO: Add checking so this doesn't execute for
        #archived slices with "DELETED" status
        #print "update status"
        try:
            with self.con:
                cur = self.con.cursor()

                #Check ap slice status in ap_slice table
                cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=%s", str(unique_id))
                cur_status = cur.fetchone()[0]

                #Check ap slice status in ap_slice_status table
                row_count = cur.execute("SELECT * FROM ap_slice_status WHERE " \
                                        "ap_slice_id=%s", str(unique_id))
                if row_count > 0:
                    ap_slice_info = cur.fetchone()
                    pre_status = ap_slice_info[1]
                    time_active = ap_slice_info[2]
                    last_active_time = ap_slice_info[3]

                #Update ap_slice_status table
                if cur_status == 'ACTIVE':
                    if row_count == 0:
                        cur.execute("INSERT INTO ap_slice_status VALUES " \
                                    "(%s,%s,'0000',Now(),0)",
                                    (str(unique_id), 'ACTIVE'))
                    else:
                        cur.execute("UPDATE ap_slice_status SET "\
                                    "status='ACTIVE', last_active_time=Now() "\
                                    "WHERE ap_slice_id=%s", (str(unique_id)))
                else:
                    if row_count > 0 and pre_status == 'ACTIVE':
                        time_diff = datetime.datetime.now() - last_active_time
                        time_active = time_active + time_diff
                        cur.execute("UPDATE ap_slice_status SET status=%s, "\
                                    "time_active=%s WHERE ap_slice_id=%s",
                                    (cur_status, self.get_time_format(time_active), str(unique_id)))
                    else:
                        cur.execute("UPDATE ap_slice_status SET status=%s "\
                                    "WHERE ap_slice_id=%s", (cur_status, str(unique_id)))
        except Exception, e:
            self.LOGGER.error("Error: %s", str(e))

    def get_time_format(self, time):
        time = time.total_seconds()
        hours = int(time // 3600)
        time = time - hours * 3600
        miniutes = int(time // 60)
        time = time - miniutes * 60
        seconds = int(time)
        time_format = str(hours) + ':' + str(miniutes) + ':' + str(seconds)
        return time_format

class StoppableThread(threading.Thread):
    """Thread class with a stop method to terminate timers
    that have been started"""
    def __init__(self, *args, **kwargs):
        kwargs = self.add_stop_argument(kwargs)
        super(StoppableThread, self).__init__(*args, **kwargs)

        self.LOGGER = get_cls_logger(self)
        self.LOGGER.debug("__init__ parent thread")
        self.LOGGER.debug(self)

    def add_stop_argument(self, kwargs):
        if 'kwargs' not in kwargs.keys():
            kwargs['kwargs'] = {}
        self._stop = threading.Event()
        kwargs['kwargs']['stop_event'] = self._stop
        return kwargs

    def stop(self):
        self._stop.set()
        #self.join()

    def stopped():
        return self._stop.is_set()

class TimerThread(StoppableThread):
    pass

#for test
#if __name__ == '__main__':
#    host = 'localhost'
#    mysql_username = 'root'
#    mysql_password = 'supersecret'
#    manager = APMonitor(None, host , mysql_username, mysql_password)
#    manager.set_status(12, True)
