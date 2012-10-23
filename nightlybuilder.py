#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import argparse
import datetime
import logging
import os
import shutil
import subprocess
import tempfile
import Queue

# local
from drewis import html, rsync, pretty

VERSION = '0.7'

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
parser.add_argument('target', help="Device(s) to build",
                    nargs='+')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
parser.add_argument('--nosync', help="Don't sync or make changelog: for testing only",
                    action="store_false")
parser.add_argument('--nobuild', help="Don't build: for testing only",
                    action="store_false")
args = parser.parse_args()

# static vars
NIGHTLY_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nightly')
SCRIPT_START = datetime.datetime.now()
DATE = SCRIPT_START.strftime('%Y.%m.%d')

# pull common env variables
droid_user = os.getenv('DROID_USER')
droid_host = os.getenv('DROID_HOST')
local_mirror = os.getenv('DROID_LOCAL_MIRROR')

if not droid_host and not droid_user and not local_mirror:
    print 'DROID_HOST or DROID_USER or DROID_LOCAL_MIRROR not set... Bailing'
    exit()

# cd working dir
previous_working_dir = os.getcwd()
os.chdir(args.source)

# upload path
upload_path = os.path.join('~', 'uploads', 'cron', DATE)

# mirror path (append to local_mirror)
mirror_path = os.path.join('cron', DATE)

# script logging
log_dir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_logs')
if os.path.isdir(log_dir) == False:
    os.mkdir(log_dir)
scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.log')
logging.basicConfig(filename=scriptlog, level=logging.INFO,
            format='%(levelname)s:%(message)s')

# make the remote directories
subprocess.call(['ssh', '%s@%s' % (droid_user, droid_host), \
                 'test -d %s || mkdir -p %s' % (upload_path,upload_path)])
if os.path.isdir(os.path.join(local_mirror, mirror_path)) == False:
    os.makedirs(os.path.join(local_mirror, mirror_path))

# upload thread
upq = Queue.Queue()
t1 = rsync.rsyncThread(upq, \
        '%s@%s:%s' % (droid_user, droid_host, upload_path), \
        message='Uploaded')
t1.setDaemon(True)
t1.start()

# mirror thread
m_q = Queue.Queue()
t2 = rsync.rsyncThread(m_q, \
        os.path.join(local_mirror, mirror_path), \
        message='Mirrored')
t2.setDaemon(True)
t2.start()

#
# Syncing
#

if args.nosync:
    # common directory for all changelogs
    changelog_dir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_changelogs')
    if os.path.isdir(changelog_dir) == False:
        os.mkdir(changelog_dir)
    # changelog
    changelog = os.path.join(changelog_dir, 'changelog-' + DATE + '.log')
    # export for sync
    os.putenv('EV_CHANGELOG', changelog)
    # sync the tree
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'sync.sh')], shell=True)
    # create the html changelog
    if os.path.exists(changelog):
        html_changelog = os.path.join(changelog_dir, 'changelog-' + DATE + '.html')
        cl = html.Create()
        cl.title('Changelog')
        clbody = html.parse_file(changelog)
        cl.header(clbody[0])
        cl.body(html.add_line_breaks(clbody[1:]))
        cl.write(html_changelog)
        # add changelog to rsync queues
        upq.put(html_changelog)
        m_q.put(changelog)
else:
    logging.info('Skipped sync')

#
# Building
#

# buildlog (only used by the build script)
buildlog_dir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_buildlogs')
if os.path.isdir(buildlog_dir) == False:
    os.mkdir(buildlog_dir)
buildlog = os.path.join(buildlog_dir, 'buildlog-' + DATE + '.log')

# export vars for the build script
os.putenv('EV_BUILDLOG', buildlog)
os.putenv('NIGHTLY_BUILD', 'true')

# for zip storage
temp_dir = tempfile.mkdtemp()

# keep track of builds
build_start = datetime.datetime.now()

# build each target
for target in args.target:
    os.putenv('EV_NIGHTLY_TARGET', target)
    # Run the build: target will be pulled from env
    if args.nobuild:
        subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'build.sh')], shell=True)
    # find and add the zips to the rsync queues
    zips = []
    target_out_dir = os.path.join('out', 'target', 'product', target)
    if os.path.isdir(target_out_dir):
        for f in os.listdir(target_out_dir):
            if f.startswith('Evervolv') and f.endswith('.zip'):
                zips.append(f)
    if zips:
        for z in zips:
            shutil.copy(os.path.join(target_out_dir, z),os.path.join(temp_dir, z))
            upq.put(os.path.join(temp_dir, z))
            m_q.put(os.path.join(temp_dir, z))
    else:
        logging.warning('No zips found for %s' % target)

# write total buildtime
with open(buildlog, 'a') as f:
    f.write('Built all targets in: %s\n' % (pretty.time(datetime.datetime.now() - build_start)))

# wait for builds to finish uploading/mirroring
m_q.join()
upq.join()

# cleanup
shutil.rmtree(temp_dir)

logging.info('Total run time: %s' % (pretty.time(datetime.datetime.now() - SCRIPT_START)))

#
# Finish up
#

# rewrite the scriptlog so build stuff is first
if os.path.exists(buildlog) and os.path.exists(scriptlog):
    with open(buildlog, 'r') as f:
        buildlog_buf = f.read()
    with open(scriptlog, 'r') as f:
        scriptlog_buf = f.read()
    with open(scriptlog, 'w') as f: # intentional truncate
        for i in buildlog_buf:
            f.write(i)
        for i in scriptlog_buf:
            f.write(i)

# create html scriptlog
if os.path.exists(scriptlog):
    html_scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.html')
    bl = html.Create()
    bl.title('Nightly Log')
    bl.header(DATE)
    bl.body(html.add_line_breaks(html.parse_file(scriptlog)))
    bl.write(html_scriptlog)
    # add log to rsync queues
    upq.put(html_scriptlog)
    m_q.put(scriptlog)
    # wait for complete
    m_q.join()
    upq.join()

# run postupload script
subprocess.call(['ssh', '%s@%s' % (droid_user,droid_host), 'test -e ~/android_scripts/updatewebsite.sh && cd ~/uploads/htdocs && ~/android_scripts/updatewebsite.sh'])

# cd previous working dir
os.chdir(previous_working_dir)
