# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import datetime
import logging
import os
import subprocess
import threading

# local
import pretty

class rsyncThread(threading.Thread):
    '''Threaded rsync task'''
    def __init__(self, queue, remote_path=None, message='Synced'):
        threading.Thread.__init__(self)
        self.queue = queue
        self.remote_path = remote_path
        self.message = message

    def run(self):
        while True:
            if self.remote_path:
                remote_path = self.remote_path
                local_file = self.queue.get()
            else:
                local_file, remote_path = self.queue.get()
            rsync(local_file, remote_path, self.message)
            self.queue.task_done()

def rsync(local_file, remote_path, message='Synced'):
    try:
        with open(os.devnull, 'w') as shadup:
            start = datetime.datetime.now()
            subprocess.check_call(['rsync', '-P', local_file, remote_path],
                        stdout=shadup, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logging.error('rsync returned %d for %s'
                    % (e.returncode, os.path.basename(local_file)))
    else:
        logging.info("%s %s in %s" % (message,
                    os.path.basename(local_file),
                    pretty.time(datetime.datetime.now() - start)))
