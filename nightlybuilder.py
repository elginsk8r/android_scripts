#!/usr/bin/env python
#
# Andrew Sutherland <dr3wsuth3rland@gmail.com>
#

import argparse
import datetime
import os
import subprocess

from drewis import html


VERSION = '0.2'
NIGHTLY_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'nightly')
DATE = datetime.datetime.now().strftime('%Y.%m.%d')

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
parser.add_argument('target', help="Device(s) to build",
                    action='append')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
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
os.putenv('EV_HTML_BUILDLOG', htmllogfile)

# changelog
changelogdir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_changelogs')
if os.path.isdir(changelogdir) == False:
    os.mkdir(changelogdir)
changelogfile = os.path.join(changelogdir, 'changelog-' + DATE + '.log')
htmlchangelogfile = os.path.join(changelogdir, 'changelog-' + DATE + '.html')
os.putenv('EV_CHANGELOG', changelogfile)
os.putenv('EV_HTML_CHANGELOG', htmlchangelogfile)

# upload path
uploadpath = os.path.join('~', 'uploads', 'cron', DATE)
os.putenv('EV_UPLOAD_PATH', uploadpath)

# pull common env variables
droiduser = os.getenv('DROID_USER')
droidhost = os.getenv('DROID_HOST')
localmirror = os.getenv('DROID_LOCAL_MIRROR')

# sync the tree
subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'sync.sh')], shell=True)

# build each target
for target in args.target:
    os.putenv('EV_NIGHTLY_TARGET', target)
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'build.sh')], shell=True)
    subprocess.call([os.path.join(NIGHTLY_SCRIPT_DIR, 'upload.sh')], shell=True)

# create html changelog
if os.path.exists(changelogfile):
    cl = html.Create()
    cl.addtitle('Changelog')
    clbody = html.parseFile(changelogfile)
    cl.addheader(clbody[0])
    cl.addbody(clbody[1:])
    cl.write(htmlchangelogfile)
# create html buildlog
if os.path.exists(buildlogfile):
    bl = html.Create()
    bl.addtitle('Buildlog')
    bl.addheader(DATE)
    bl.addbody(html.parseFile(logfile))
    bl.write(htmllogfile)
# upload the html files
if droiduser and droidhost:
    subprocess.call([ 'rsync', '-P', htmllogfile, htmlchangelogfile, droiduser + '@' + droidhost + ':' + uploadpath ])
# mirror the log files
if localmirror:
    subprocess.call([ 'rsync', '-P', logfile, changelogfile, os.path.join(localmirror, 'cron', DATE)])


# cd previous working dir
os.chdir(previous_working_dir)