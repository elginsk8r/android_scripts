#!/usr/bin/env python
#
# Andrew Sutherland <dr3wsuth3rland@gmail.com>
#

import argparse
import datetime
import os
import subprocess

from drewis import html


VERSION = '0.3'
NIGHTLY_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nightly')
DATE = datetime.datetime.now().strftime('%Y.%m.%d')

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
parser.add_argument('target', help="Device(s) to build",
                    action='append')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
parser.add_argument('--nosync', help="Don't sync or create changelog, for testing",
                    action="store_true")
args = parser.parse_args()

# cd working dir
previous_working_dir = os.getcwd()
os.chdir(args.source)

# set common env variables
os.putenv('NIGHTLY_BUILD', 'true')

# buildlog
buildlogdir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_buildlogs')
if os.path.isdir(buildlogdir) == False:
    os.mkdir(buildlogdir)
logfile = os.path.join(buildlogdir, 'buildlog-' + DATE + '.log')
htmllogfile = os.path.join(buildlogdir, 'buildlog-' + DATE + '.html')
os.putenv('EV_BUILDLOG', logfile)

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

# build each target
for target in args.target:
    os.putenv('EV_NIGHTLY_TARGET', target)
    # Run the build: target will be pulled from env
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'build.sh')], shell=True)
    # find, upload and mirror the zips
    # TODO: copy the files out and upload asyncronously while continuing to
    #       build other targets
    zips = []
    for files in os.listdir(os.path.join('out', 'target', 'product', target)):
        if files.startswith('Evervolv') and files.endswith('.zip'):
            zips.append(files)
    if zips and droiduser and droidhost:
        for zipfile in zips:
            subprocess.call(['rsync', '-P', zipfile, droiduser + '@' + droidhost + ':' + uploadpath ])
    if zips and localmirror:
        for zipfile in zips:
            subprocess.call(['rsync', '-P', zipfile, os.path.join(localmirror, mirrorpath)])

# create html changelog
if os.path.exists(changelogfile):
    cl = html.Create()
    cl.addtitle('Changelog')
    clbody = html.parseFile(changelogfile)
    cl.addheader(clbody[0])
    cl.addbody(clbody[1:])
    cl.write(htmlchangelogfile)
# create html buildlog
if os.path.exists(logfile):
    bl = html.Create()
    bl.addtitle('Buildlog')
    bl.addheader(DATE)
    bl.addbody(html.parseFile(logfile))
    bl.write(htmllogfile)
# upload the html files
if droiduser and droidhost:
    subprocess.call(['rsync', '-P', htmllogfile, htmlchangelogfile, droiduser + '@' + droidhost + ':' + uploadpath ])
# mirror the log files
if localmirror:
    subprocess.call(['rsync', '-P', logfile, changelogfile, os.path.join(localmirror, mirrorpath)])

# cd previous working dir
os.chdir(previous_working_dir)
