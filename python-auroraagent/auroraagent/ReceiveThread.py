import threading

class ReceiveThread(threading.Thread):
    def __init__(self, receive_callback):
        threading.Thread.__init__(self)
        # self.socket = str(socket)
        self.receive_callback = receive_callback

    def run(self):
        self.receive_callback()