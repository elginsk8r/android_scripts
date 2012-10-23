# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import datetime
import logging
import os
import subprocess
import threading

class rsyncThread(threading.Thread):
    '''Threaded rsync task'''
    def __init__(self, queue, p_remote, message='Synced'):
        threading.Thread.__init__(self)
        self.queue = queue
        self.p_remote = p_remote
        self.message = message

    def run(self):
        while True:
            f_local = self.queue.get()
            rsync(f_local, self.p_remote, self.message)
            self.queue.task_done()

def rsync(local_file, remote_path, message='Synced'):
    try:
        with open(os.devnull, 'w') as shadup:
            start = datetime.datetime.now()
            subprocess.check_call(['rsync', '-P', local_file, remote_path], \
                        stdout=shadup, stderr=subprocess.STDOUT)
            finish = datetime.datetime.now()
    except subprocess.CalledProcessError as e:
        logging.error('rsync returned %d for %s' \
                    % (e.returncode, os.path.basename(local_file)))
    else:
        logging.info("%s %s in %s" % (message, \
                    os.path.basename(local_file), \
                    finish - start))
