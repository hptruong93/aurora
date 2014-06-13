import threading
import subprocess
import random

class Call(threading.Thread):

    def __init__ (self):
        threading.Thread.__init__(self)

    def run(self):
        while random.randint(0, 10) > 1:
            subprocess.check_call(["aurora", "ap-list"])
            subprocess.check_call(["aurora", "ap-slice-list"])

threads = []
for num in range(0, 50):
    thread = Call()
    thread.start()
    threads.append(thread)

for t in threads:
    t.join()

print "Done"
