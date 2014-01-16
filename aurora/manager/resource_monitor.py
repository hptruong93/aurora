import MySQLdb as mdb
import atexit
import sys


class resourceMonitor():
    
    sql_locked = None
    
    def __init__(self, dispatcher, host, username, password):
        self.dispatcher = dispatcher
        
        #Connect to Aurora mySQL Database
        print "Connecting to SQLdb in resourceMonitor..."
        try:
            self.con = mdb.connect(host, username, password, 'aurora')
            resourceMonitor.sql_locked = False
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
        
        atexit.register(self.closeSQL)
    
    def closeSQL(self):
        print "Closing SQL connection in resourceMonitor..."
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')
    
    def timeout(self, unique_id):
        """This code will execute when a response is not
        received for the command associated with the unique_id
        after a certain time period.  It modifies the database
        to reflect the current status of the AP."""

        # A timeout is serious: it is likely that
        # the AP's OS has crashed, or at least aurora is
        # no longer running.
        
        self.set_status(unique_id, success=False, ap_up=False)
                
        # In the future we might do something more with the unique_id besides
        # identifying the AP, like log it to a list of commands that cause
        # AP failure, but for now it's good enough to know that our AP
        # has died and at least this command failed
        # If there are several commands waiting, this will execute several times
        # but all slices should already be marked
        # as deleted, down or failed, so there will not be any issue
        
    
    
    def set_status(self, unique_id, success, ap_up=True):
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
                    
                    else:
                        print("Unknown Status, ignoring...")
                
                # Access point down, mark all slices and failed/down
                else:
                    to_execute = "SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'"
                    print to_execute
                    cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                    physical_ap = cur.fetchone()
                    if physical_ap:
                        physical_ap = physical_ap[0]
                    else:
                        raise Exception("Cannot fetch physical_ap for slice %s\n" % unique_id)
                    #Get all slices associated with this ap
                    cur.execute("SELECT ap_slice_id FROM ap_slice WHERE physical_ap=\'"+str(physical_ap)+"\'")
                    
                    #Prune List of ap_slice_id
                    raw_list = cur.fetchall()
                    if raw_list:
                        slice_list = []
                        for entry in raw_list:
                            slice_list.append(entry[0])
                    else:
                        raise Exception("Cannot slices from physical_ap '%s'\n" % physical_ap)
                    
                    slice_list = []
                    
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
                print "Database Error: " + str(e)
        finally:
            resourceMonitor.sql_locked = False

        
    def reset_AP(self, ap):
        """Reset the access point.  If there are serious issues, however,
        a restart may be required."""
        
        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'reset' } , ap, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        
    def restart_AP(self, ap):
        """Restart the access point, telling the OS to reboot."""
        
        # The unique ID is fixed to be all F's for resets/restarts.
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'restart' } , ap, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        
        
