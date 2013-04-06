# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import datetime
import logging
import os
import subprocess
import threading

# local
from utils import pretty_time

class rsyncThread(threading.Thread):
    '''Threaded rsync task'''
    def __init__(self, queue, remote_path=None, port=None, message='Synced'):
        threading.Thread.__init__(self)
        self.queue = queue
        self.remote_path = remote_path
        self.port = port
        self.message = message

    def run(self):
        while True:
            if self.remote_path:
                remote_path = self.remote_path
                local_file = self.queue.get()
            else:
                local_file, remote_path = self.queue.get()
            rsync(local_file, remote_path, self.port, self.message)
            self.queue.task_done()

def rsync(local_file, remote_path, port=None, message='Synced'):
    try:
        start = datetime.datetime.now()
        if port:
            subprocess.check_call(['rsync', '-e ssh -p%s' % (port),
                    '-pq', local_file, remote_path])
        else:
            subprocess.check_call(['rsync', '-pq', local_file, remote_path])
    except subprocess.CalledProcessError as e:
        logging.error('rsync returned %d for %s'
                    % (e.returncode, os.path.basename(local_file)))
    else:
        logging.info("%s %s in %s" % (message,
                    os.path.basename(local_file),
                    pretty_time(datetime.datetime.now() - start)))
