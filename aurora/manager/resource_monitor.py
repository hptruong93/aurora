class resourceMonitor():

    

    def timeout(self, unique_id):
        pass
        
    def send_ping(self):
        pass
    
    
    def set_status(self, unique_id, status):
        """Sets the status of the associated request in the
        database based on the previous status, i.e. pending -> active if
        create slice, deleting -> deleted if deleting a slice, etc."""
        pass
        
    def reset_AP(self, ap):
        pass
