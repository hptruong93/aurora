import MySQLdb as mdb
import atexit
import sys, uuid
import accountingManager
import threading
import time

class resourceMonitor():


    #TODO: Query SQL db for slices with status other than 'DELETED'
    #and ping associated ap to determine whether they are still up

    sql_locked = None
    SLEEP_TIME = 45

    def __init__(self, aurora_db, dispatcher, host, username, password):
        self.dispatcher = dispatcher
        self.aurora_db = aurora_db
        self.accountingManager = accountingManager.accountingManager(host, username, password)
        self.poller_threads = {}
        #Connect to Aurora mySQL Database
        print "Connecting to SQLdb in resourceMonitor..."
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
            resourceMonitor.sql_locked = False
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)

        atexit.register(self._closeSQL)

    def stop(self):
        self._close_all_poller_threads()

    def _closeSQL(self):
        print "Closing SQL connection in resourceMonitor..."
        self.aurora_db.ap_status_unknown()
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')

    def _close_all_poller_threads(self):
        for ap_name in self.poller_threads.keys():
            self._close_poller_thread(ap_name, 'admin')

    def _close_poller_thread(self, ap_name, unique_id):
        if ap_name in self.poller_threads and unique_id == 'admin':
            poller_thread = self.poller_threads.pop(ap_name)
            print "Stopping thread",ap_name,poller_thread
            poller_thread.stop()

    def timeout(self, unique_id, ap_name):
        """This code will execute when a response is not
        received for the command associated with the unique_id
        after a certain time period.  It modifies the database
        to reflect the current status of the AP."""


        print type(unique_id), unique_id
        # A timeout is serious: it is likely that
        # the AP's OS has crashed, or at least aurora is
        # no longer running.
        
        if unique_id != 'admin':
            self.set_status(unique_id, success=False, ap_up=False)
        else:
            self.set_status(unique_id, success=False, ap_up=False, ap_name=ap_name)
        #remove thread from the thread pool
        
        self._close_poller_thread(ap_name, unique_id)

        # In the future we might do something more with the unique_id besides
        # identifying the AP, like log it to a list of commands that cause
        # AP failure, but for now it's good enough to know that our AP
        # has died and at least this command failed
        # If there are several commands waiting, this will execute several times
        # but all slices should already be marked
        # as deleted, down or failed, so there will not be any issue

    def update_records(self, message):
        """Update the traffic information of ap_slice"""
        self.accountingManager.update_traffic(message)

    def set_status(self, unique_id, success, ap_up=True, ap_name = None):
        """Sets the status of the associated request in the
        database based on the previous status, i.e. pending -> active if
        create slice, deleting -> deleted if deleting a slice, etc.
        If the ap_up variable is false, the access point
        is considered to be offline and in an unknown state,
        so *all* slices are marked as such (down, failed, etc.)."""

        # DEBUG
        print("Updating ap status for ID " + str(unique_id) + ".\nRequest successful: " + str(success) + "\nAccess Point up: " + str(ap_up))
        if resourceMonitor.sql_locked:
            print "SQL Access is locked, waiting..."
            while resourceMonitor.sql_locked:
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
                resourceMonitor.sql_locked = True
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

                    self.aurora_db.ap_status_down(physical_ap)

        except Exception, e:
                print "Database Error: " + str(e)
        finally:
            resourceMonitor.sql_locked = False


        self.accountingManager.update_status(unique_id, ap_up, ap_name)

    def restart_slices(self, ap, slice_list):
        if resourceMonitor.sql_locked:
            print "SQL Access is locked, waiting..."
            while resourceMonitor.sql_locked:
                pass
        try:
            with self.con:
                resourceMonitor.sql_locked = True
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
                        self.dispatcher.dispatch( { 'slice': slice_id,
                                                    'command': 'restart_slice',
                                                    'user': user_id},
                                                  ap,
                                                  str(uuid.uuid4()) )
        except Exception, e:
            print "Database Error: " + str(e)
        finally:
            resourceMonitor.sql_locked = False

    def start_poller(self, ap_name):
        print "Starting poller on thread ",
        #poller_thread = thread(ThreadClass, self)
        poller_thread = TimerThread(target=self.poll_AP, args=(ap_name,))
        print poller_thread
        self.poller_threads[ap_name] = poller_thread
        poller_thread.start()

    def poll_AP(self, ap_name, stop_event=None):
        print "Timeout from Dispatcher", self.dispatcher.TIMEOUT
        while ap_name in self.poller_threads:
            #time.sleep(resourceMonitor.SLEEP_TIME)
            if stop_event.is_set():
                "Poller thread for",ap_name,"is dying now!"
                break
            print "Updating ap in poller thread",self.poller_threads[ap_name]
            self.update_AP(ap_name)
            for i in range(self.dispatcher.TIMEOUT + 5):
                if stop_event.is_set():
                    break
                time.sleep(1)

    def reset_AP(self, ap):
        """Reset the access point.  If there are serious issues, however,
        a restart may be required."""

        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'reset' } , ap, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')

    def restart_AP(self, ap):
        """Restart the access point, telling the OS to reboot."""

        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'restart' } , ap, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')

    def update_AP(self, ap):
        """Update the access point """

        # The unique ID is fixed to be all F's
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'update'}, ap , 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')

class TimerThread(threading.Thread):
    """Thread class with a stop method to terminate timers
    that have been started"""
    def __init__(self, *args, **kwargs):
        self._stop = threading.Event()
        if 'kwargs' not in kwargs.keys():
            kwargs['kwargs'] = {}
        kwargs['kwargs']['stop_event'] = self._stop
        super(TimerThread, self).__init__(*args, **kwargs)

    def stop(self):
        self._stop.set()
        self.join()

    def stopped():
        return self._stop.is_set()

#for test
#if __name__ == '__main__':
#    host = 'localhost'
#    mysql_username = 'root'
#    mysql_password = 'supersecret'
#    manager = resourceMonitor(None, host , mysql_username, mysql_password)
#    manager.set_status(12, True)
