# Python capsulator class
# Configures and runs the capsulator program developed by Stanford

import subprocess
class Capsulator:    

    def __init__(self):
        self.process_list = {}

    def start(self):
        
        command = ["gedit"]

        process = subprocess.Popen(command)
        self.process_list[process.pid] = process
        
        return process.pid
        

    def stop(self, pid):
        
        process = self.process_list.pop(pid)
        process.terminate()
        process.wait()


    def kill_all(self):
        for key in self.process_list:
            self.process_list[key].terminate()
