class resourceMonitor():

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        #Connect to Aurora mySQL Database
        try:
            self.con = mdb.connect('localhost', 'root', 'supersecret', 'aurora') #Change address
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])
            sys.exit(1)
    
    def closeSQL(self):
        if self.con:
            self.con.close()
        else:
            print('Connection already closed!')
    
    def timeout(self, unique_id):
        """This code will execute when a response is not
        received for the command associated with the unique_id
        after a certain time period.  It modifies the database
        to reflect the current status of the AP."""
        print("TIMEOUT OF " + str(unique_id))
        # A timeout is serious: it is likely that
        # the AP's OS has crashed, or at least aurora is
        # no longer running.
        
        # use set_status
        # TODO: DATABASE
        # Identify AP from unique_id of command
        # for all slices and/or commands relating to AP:
        #   if slice is active, mark down
        #   else if slice is deleting, mark deleted (will be when we reinitialize)
        #   else if slice is pending, mark failed
        try:
            with self.con:
                cur = self.con.cursor()
                cur.execute("SELECT physical_ap FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                physical_ap = cur.fetchone()[0]
                #Get all slices associated with this ap
                cur.execute("SELECT ap_slice_id FROM ap_slice WHERE physical_ap=\'"+str(physical_ap)+"\'")
                #Prune List of ap_slice_id
                raw_list = cur.fetchall()
                slice_list = []
                for entry in raw_list:
                    slice_list.append(entry[0])
                
                #Change status accordingly
                for entry in slice_list:
                    #Get status
                    cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=\'"+str(entry)+"\'")
                    status = cur.fetchone()[0]
                    if status == 'ACTIVE':
                        cur.execute("UPDATE ap_slice SET status='DOWN' WHERE ap_slice_id=\'"+str(entry)+"\'")
                    elif status == 'DELETING':
                        cur.execute("UPDATE ap_slice SET status='DELETED' WHERE ap_slice_id=\'"+str(entry)+"\'")
                    elif status == 'PENDING':
                        cur.execute("UPDATE ap_slice SET status='FAILED' WHERE ap_slice_id=\'"+str(entry)+"\'")
                    else:
                        print("Unknown Status, ignoring...")
            
        except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        
        self.closeSQL()
                
        # In the future we might do something more with the unique_id besides
        # identifying the AP, like log it to a list of commands that cause
        # AP failure, but for now it's good enough to know that our AP
        # has died and at least this command failed
        # If there are several commands waiting, this will execute several times
        # but all slices should already be marked
        # as deleted, down or failed, so the above loop does nothing
        
    
    
    def set_status(self, unique_id, success, ap_up=True):
        """Sets the status of the associated request in the
        database based on the previous status, i.e. pending -> active if
        create slice, deleting -> deleted if deleting a slice, etc."""
        print("SETTING STATUS OF " + str(unique_id) + " to " + str(success))
        # TODO: DATABASE
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
                cur = self.con.cursor()
                #Change status accordingly
                #Get status
                cur.execute("SELECT status FROM ap_slice WHERE ap_slice_id=\'"+str(unique_id)+"\'")
                status = cur.fetchone()[0]
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
            
        except mdb.Error, e:
                print "Error %d: %s" % (e.args[0], e.args[1])
        
        self.closeSQL()
        
        
    def reset_AP(self, ap):
        self.dispatcher.dispatch( { 'slice' : 'admin', 'command' : 'restart' } , ap, 'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        
