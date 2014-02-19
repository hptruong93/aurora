import atexit
import collections
import sys
import threading
import time
import uuid
import weakref

import MySQLdb as mdb

import accounting_manager

class ResourceMonitor(object):


    # Make function to determine if dispatcher still exists

    sql_locked = None
    SLEEP_TIME = 45

    def __init__(self, dispatcher, host, username, password):
        self.dispatcher_ref = weakref.ref(dispatcher)
        print "[resource_monitor]: Made weak ref",self.dispatcher_ref, self.dispatcher_ref()

        self.aurora_db = self.dispatcher_ref().aurora_db
        self.am = accounting_manager.AccountingManager(host, username, password)
        self.poller_threads = {}

        # To handle incoming status update requests, make a command queue
        self.timeout_queue = collections.deque()
        self._make_queue_daemon()

        #Connect to Aurora mySQL Database
        print "Connecting to SQLdb in ResourceMonitor..."
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
            ResourceMonitor.sql_locked = False
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

        atexit.register(self._closeSQL)

    def _closeSQL(self):
        print "Closing SQL connection in ResourceMonitor..."
        self.aurora_db.ap_status_unknown()
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')

    def _make_queue_daemon(self):
        print "[resource_monitor.py]: Creating Queue Daemon"
        self.qd = StoppableThread(target=self._watch_queue)
        self.qd.start()

    def _watch_queue(self, stop_event=None):
        while True:
            while len(self.timeout_queue) < 1 and not stop_event.is_set():
                time.sleep(1)
            if stop_event.is_set():
                print "[resource_monitor.py]: Queue Daemon caught stop event"
                break
            (args, kwargs) = self.timeout_queue.popleft()
            self._set_status(*args, **kwargs)

    def _add_call_to_queue(self, *args, **kwargs):
        self.timeout_queue.append((args, kwargs))

    def stop(self):
        self._close_all_poller_threads()
        self.qd.stop()

    def _close_all_poller_threads(self):
        print "[ResourceMonitor]: Closing all threads"
        print "[ResourceMonitor]: %s" % self.poller_threads
        for ap_name in self.poller_threads.keys():
            self._close_poller_thread(ap_name, 'admin')

    def _close_poller_thread(self, ap_name, unique_id):
        if ap_name in self.poller_threads and unique_id == 'admin':
            poller_thread = self.poller_threads.pop(ap_name)
            print "Stopping thread",ap_name,poller_thread
            poller_thread.stop()

    def timeout(self, ap_slice_id, ap_name, message_uuid = None):
        """This code will execute when a response is not
        received for the command associated with the unique_id
        after a certain time period.  It modifies the database
        to reflect the current status of the AP."""

        if message_uuid is not None:
            dispatcher = self.dispatcher_ref()
            if dispatcher is None:
                print "[resource_monitor]: Dispatcher has been deallocated"
            else:
                dispatcher.remove_request(message_uuid)
        print "[ResourceMonitor]: %s %s" % (type(ap_slice_id), ap_slice_id)
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
        self.am.update_traffic(message)

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
            print("Updating ap status for ID " + str(unique_id) + ".\nRequest successful: " + str(success) + "\nAccess Point up: " + str(ap_up))
        else:
            print("Updating ap status for ID " + str(ap_name) + ".\nRequest successful: " + str(success) + "\nAccess Point up: " + str(ap_up))

        if ResourceMonitor.sql_locked:
            print "SQL Access is locked, waiting..."
            while ResourceMonitor.sql_locked:
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
                ResourceMonitor.sql_locked = True
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
                        print("Unknown Status, ignoring...")

                # Access point down, mark all slices and failed/down
                else:
                    if ap_name:
                        physical_ap = ap_name
                    else:
                        to_execute = "SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'"
                        print to_execute
                        cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                        physical_ap = cur.fetchone()
                        if physical_ap:
                            physical_ap = physical_ap[0]
                        else:
                            raise Exception("Cannot fetch physical_ap for slice %s\n" % unique_id)

                    print "physical_ap:",physical_ap
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

                    print "raw_list:",raw_list
                    print "slice_list:",slice_list

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
                            print "%s: %s >>> Updated to status: 'DOWN'" % (entry, status)
                        elif status == 'DELETING':
                            cur.execute("UPDATE ap_slice SET status='DELETED' WHERE ap_slice_id=\'"+str(entry)+"\'")
                            print "%s: %s >>> Updated to status: 'DELETED'" % (entry, status)
                        elif status == 'PENDING':
                            cur.execute("UPDATE ap_slice SET status='FAILED' WHERE ap_slice_id=\'"+str(entry)+"\'")
                            print "%s: %s >>> Updated to status: 'FAILED'" % (entry, status)
                        else:
                            print("%s: %s >>> Unknown Status, ignoring..." % (entry, status))

        except Exception, e:
                print "[ResourceMonitor]: " + str(e)
        finally:
            ResourceMonitor.sql_locked = False


        self.am.update_status(unique_id, ap_up, ap_name)

        return True

    def restart_slices(self, ap, slice_list):
        if ResourceMonitor.sql_locked:
            print "SQL Access is locked, waiting..."
            while ResourceMonitor.sql_locked:
                pass
        try:
            with self.con:
                ResourceMonitor.sql_locked = True
                cur = self.con.cursor()
                for slice_id in slice_list:
                    print "Restarting", slice_id
                    cur.execute("SELECT status, tenant_id FROM ap_slice WHERE ap_slice_id = '%s'" %
                                slice_id)
                    items = cur.fetchone()
                    if items:
                        status = items[0]
                        user_id = items[1]
                        print "%s %s for tenant %s" % (slice_id, status, user_id)
                    else:
                        raise Exception("No slice %s\n" % slice_id)
                    if status != 'DELETED' and status != 'DELETING':
                        # Restart slice as it wasn't deleted since AP went down
                        dispatcher = self.dispatcher_ref()
                        dispatcher.dispatch({ 'slice': slice_id,
                                                   'command': 'restart_slice',
                                                   'user': user_id},
                                                 ap)
        except Exception, e:
            print "Database Error: " + str(e)
        finally:
            ResourceMonitor.sql_locked = False

    def start_poller(self, ap_name):
        print "Starting poller on thread ",
        #poller_thread = thread(ThreadClass, self)
        poller_thread = TimerThread(target=self.poll_AP, args=(ap_name,))
        print poller_thread
        self.poller_threads[ap_name] = poller_thread
        poller_thread.start()

    def poll_AP(self, ap_name, stop_event=None):
        #print "Timeout from Dispatcher", self.dispatcher.TIMEOUT
        own_thread = self.poller_threads[ap_name]
        while ap_name in self.poller_threads:
            #time.sleep(ResourceMonitor.SLEEP_TIME)
            print "[ResourceMonitor]: %s thread is %s" % (ap_name, own_thread)
            self.get_stats(ap_name)
            dispatcher = self.dispatcher_ref()
            for i in range(dispatcher.TIMEOUT + 5):
                if stop_event.is_set():
                    print "[ResourceMonitor]: Caught stop event for %s" % own_thread
                    break
                time.sleep(1)
            if stop_event.is_set():
                print "[ResourceMonitor]: Poller thread for %s is dying now" % ap_name
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

class StoppableThread(threading.Thread):
    """Thread class with a stop method to terminate timers
    that have been started"""
    def __init__(self, *args, **kwargs):
        self._stop = threading.Event()
        if 'kwargs' not in kwargs.keys():
            kwargs['kwargs'] = {}
        kwargs['kwargs']['stop_event'] = self._stop
        print "[StoppableThread]: __init__ parent thread", 
        super(StoppableThread, self).__init__(*args, **kwargs)
        print self

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
#    manager = ResourceMonitor(None, host , mysql_username, mysql_password)
#    manager.set_status(12, True)
