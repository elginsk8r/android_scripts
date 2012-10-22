#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import argparse
import datetime
import os
import shutil
import subprocess
import tempfile
import threading
import Queue

from drewis import html

VERSION = '0.5'

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
parser.add_argument('target', help="Device(s) to build",
                    nargs='+')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
parser.add_argument('--nosync', help="Don't sync or create changelog, for testing",
                    action="store_true")
args = parser.parse_args()

# static vars
NIGHTLY_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nightly')
DATE = datetime.datetime.now().strftime('%Y.%m.%d')

# fuctions
def write_log(message):
    with open(LOG_FILE, 'a') as f:
        f.write(message + '\n')

def run_rsync(local_file, remote_path, message='Synced'):
    try:
        with open(os.devnull, 'w') as shadup:
            subprocess.check_call(['rsync', '-P', local_file, remote_path], \
                        stdout=shadup, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        write_log('FAIL: rsync returned %d for %s' \
                    % (e.returncode, os.path.basename(local_file)))
    else:
        write_log('%s: %s' % (message, os.path.basename(local_file)))

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
            run_rsync(f_local, self.p_remote, self.message)
            self.queue.task_done()

# cd working dir
previous_working_dir = os.getcwd()
os.chdir(args.source)

# set common env variables
os.putenv('NIGHTLY_BUILD', 'true')

# buildlog
buildlogdir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_buildlogs')
if os.path.isdir(buildlogdir) == False:
    os.mkdir(buildlogdir)
LOG_FILE = os.path.join(buildlogdir, 'buildlog-' + DATE + '.log')
htmllogfile = os.path.join(buildlogdir, 'buildlog-' + DATE + '.html')
os.putenv('EV_BUILDLOG', LOG_FILE)

# changelog
changelogdir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_changelogs')
if os.path.isdir(changelogdir) == False:
    os.mkdir(changelogdir)
changelogfile = os.path.join(changelogdir, 'changelog-' + DATE + '.log')
htmlchangelogfile = os.path.join(changelogdir, 'changelog-' + DATE + '.html')
os.putenv('EV_CHANGELOG', changelogfile)

# upload path
uploadpath = os.path.join('~', 'uploads', 'cron', DATE)

# mirror path (append to localmirror)
mirrorpath = os.path.join('cron', DATE)

# pull common env variables
droiduser = os.getenv('DROID_USER')
droidhost = os.getenv('DROID_HOST')
localmirror = os.getenv('DROID_LOCAL_MIRROR')

# sync the tree
if args.nosync == False:
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'sync.sh')], shell=True)

# make the remote directories
if droiduser and droidhost:
    subprocess.call(['ssh', '%s@%s' % (droiduser, droidhost), \
                'test -d %s || mkdir -p %s' % (uploadpath,uploadpath)])
if localmirror:
    if os.path.isdir(os.path.join(localmirror, mirrorpath)) == False:
        os.makedirs(os.path.join(localmirror, mirrorpath))

# upload thread
up_q = Queue.Queue()
t = rsyncThread(up_q, \
                '%s@%s:%s' % (droiduser, droidhost, uploadpath), \
                message='Uploaded')
t.setDaemon(True)
t.start()

# mirror thread
m_q = Queue.Queue()
t2 = rsyncThread(m_q, \
                 os.path.join(localmirror, mirrorpath), \
                 message='Mirrored')
t2.setDaemon(True)
t2.start()

# for zip storage
temp_dir = tempfile.mkdtemp()

# keep track
build_start = datetime.datetime.now()

# build each target
for target in args.target:
    os.putenv('EV_NIGHTLY_TARGET', target)
    # Run the build: target will be pulled from env
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'build.sh')], shell=True)
    # find and add the zips to the rsync queues
    zips = []
    target_out_dir = os.path.join('out', 'target', 'product', target)
    for f in os.listdir(target_out_dir):
        if f.startswith('Evervolv') and f.endswith('.zip'):
            zips.append(f)
    if zips:
        for z in zips:
            shutil.copy(os.path.join(target_out_dir, z),os.path.join(temp_dir, z))
            if droiduser and droidhost:
                up_q.put(os.path.join(temp_dir, z))
            else:
                write_log('Skipping upload for %s' % z)
            if localmirror:
                m_q.put(os.path.join(temp_dir, z))
            else:
                write_log('Skipping mirror for %s' % z)

# log our buildtime
write_log('Total build time: %s' % (datetime.datetime.now() - build_start))

# wait for rsync to complete
m_q.join()
up_q.join()
# cleanup
shutil.rmtree(temp_dir)

# create html changelog
if os.path.exists(changelogfile):
    cl = html.Create()
    cl.title('Changelog')
    clbody = html.parse_file(changelogfile)
    cl.header(clbody[0])
    cl.body(html.add_line_breaks(clbody[1:]))
    cl.write(htmlchangelogfile)

# create html buildlog
if os.path.exists(LOG_FILE):
    bl = html.Create()
    bl.title('Buildlog')
    bl.header(DATE)
    bl.body(html.add_line_breaks(html.parse_file(LOG_FILE)))
    bl.write(htmllogfile)

# upload the html files
if droiduser and droidhost:
    if os.path.exists(htmllogfile):
        run_rsync(htmllogfile, '%s@%s:%s' % (droiduser, droidhost, uploadpath),
                    'Uploaded')
    if os.path.exists(htmlchangelogfile):
        run_rsync(htmlchangelogfile, '%s@%s:%s' % (droiduser, droidhost, uploadpath), \
                    'Uploaded')

# mirror the log files
if localmirror:
    if os.path.exists(LOG_FILE):
        run_rsync(LOG_FILE, os.path.join(localmirror, mirrorpath), \
                    'Mirrored')
    if os.path.exists(changelogfile):
        run_rsync(changelogfile, os.path.join(localmirror, mirrorpath), \
                    'Mirrored')

# run postupload script
subprocess.call(['ssh', '%s@%s' % (droiduser,droidhost), 'test -e ~/android_scripts/updatewebsite.sh && cd ~/uploads/htdocs && ~/android_scripts/updatewebsite.sh'])

# cd previous working dir
os.chdir(previous_working_dir)
