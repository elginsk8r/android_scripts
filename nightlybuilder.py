#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import argparse
import datetime
import os
import subprocess

from drewis import html


VERSION = '0.4'
NIGHTLY_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nightly')
DATE = datetime.datetime.now().strftime('%Y.%m.%d')
LOG_FILE = '' # This is assigned later, just letting you know

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
subprocess.call(['ssh', '%s@%s' % (droiduser, droidhost), \
            'test -d %s || mkdir -p %s' % (uploadpath,uploadpath)])
if os.path.isdir(os.path.join(localmirror, mirrorpath)) == False:
    os.makedirs(os.path.join(localmirror, mirrorpath))

# build each target
for target in args.target:
    os.putenv('EV_NIGHTLY_TARGET', target)
    # Run the build: target will be pulled from env
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'build.sh')], shell=True)
    # find, upload and mirror the zips
    # TODO: copy the files out and upload asyncronously while continuing to
    #       build other targets
    zips = []
    targetoutdir = os.path.join('out', 'target', 'product', target)
    for f in os.listdir(targetoutdir):
        if f.startswith('Evervolv') and f.endswith('.zip'):
            zips.append(f)
    if zips:
        for z in zips:
            if droiduser and droidhost:
                run_rsync(os.path.join(targetoutdir, z), \
                            '%s@%s:%s' % (droiduser, droidhost, uploadpath), \
                            'Uploaded')
            else:
                write_log('Skipping upload for %s' % z)
            if localmirror:
                run_rsync(os.path.join(targetoutdir, z), \
                            os.path.join(localmirror, mirrorpath), \
                            'Mirrored')
            else:
                write_log('Skipping mirror for %s' % z)

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
