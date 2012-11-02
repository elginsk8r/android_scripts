#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import argparse
from datetime import datetime
import logging
import os
import shutil
import subprocess
import tempfile
import Queue

# local
from drewis import html, rsync, pretty
from drewis.__version__ import __version__

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
parser.add_argument('target', help="Device(s) to build",
                    nargs='+')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
parser.add_argument('--host', help="Hostname for upload")
parser.add_argument('--user', help="Username for upload host")
parser.add_argument('--mirror', help="Path for upload mirroring")
parser.add_argument('--nosync', help=argparse.SUPPRESS,
                    action="store_true")
parser.add_argument('--nobuild', help=argparse.SUPPRESS,
                    action="store_true")
args = parser.parse_args()

# static vars
HELPER_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'helpers')
DATE = datetime.now().strftime('%Y.%m.%d')

# script logging
log_dir = os.path.join(args.source, 'nightly_logs')
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)
scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.log')
logging.basicConfig(filename=scriptlog, level=logging.INFO,
        format='%(levelname)s:%(message)s')

def handle_build_errors(error_file):
    grepcmds = [
        ('GCC:', ('grep', '-B 1', '-A 2', '-e error:')),
        ('JAVA:', ('grep', '-B 10', '-e error$')), # combine these someday
        ('JAVA:', ('grep', '-B 20', '-e errors$')),
        ('MAKE:', ('grep', '-e \*\*\*\ '))] # No idea why ^make won't work
    with open(error_file) as f:
        logging.error('Dumping errors...')
        for grepcmd in grepcmds:
            try:
                errors = subprocess.check_output(grepcmd[1], stdin=f)
            except subprocess.CalledProcessError as e:
                pass
            else:
                if errors:
                    logging.error(grepcmd[0])
                    for line in errors.split('\n'):
                        logging.error(line)
            f.seek(0)
        logging.error('Hopefully that helps')

def main(args):

    # for total runtime
    script_start = datetime.now()

    # set vars for uploading/mirroring
    if not args.user:
        droid_user = os.getenv('DROID_USER')
    else:
        droid_user = args.user
    if not args.host:
        droid_host = os.getenv('DROID_HOST')
    else:
        droid_host = args.host
    if not args.mirror:
        local_mirror = os.getenv('DROID_MIRROR')
        if not local_mirror:
            local_mirror = os.getenv('DROID_LOCAL_MIRROR')
    else:
        local_mirror = args.mirror

    # these vars are mandatory
    if not droid_host or not droid_user or not local_mirror:
        print 'DROID_HOST or DROID_USER or DROID_LOCAL_MIRROR not set... Bailing'
        exit()

    # cd working dir
    previous_working_dir = os.getcwd()
    os.chdir(args.source)

    # upload path
    upload_path = os.path.join('~', 'uploads', 'cron', DATE)

    # mirror path
    mirror_path = os.path.join(local_mirror, 'cron', DATE)

    # make the remote directories
    try:
        subprocess.check_call(['ssh', '%s@%s' % (droid_user, droid_host),
                'test -d %s || mkdir -p %s' % (upload_path,upload_path)])
    except subprocess.CalledProcessError as e:
        logging.error('ssh returned %d while making directories' % (e.returncode))

    if not os.path.isdir(mirror_path):
        os.makedirs(mirror_path)

    # upload thread
    upq = Queue.Queue()
    t1 = rsync.rsyncThread(upq,
            '%s@%s:%s' % (droid_user, droid_host, upload_path),
            message='Uploaded')
    t1.setDaemon(True)
    t1.start()

    # mirror thread
    m_q = Queue.Queue()
    t2 = rsync.rsyncThread(m_q,
            mirror_path,
            message='Mirrored')
    t2.setDaemon(True)
    t2.start()

    #
    # Syncing
    #

    if not args.nosync:
        # common directory for all changelogs
        changelog_dir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_changelogs')
        if not os.path.isdir(changelog_dir):
            os.mkdir(changelog_dir)
        # changelog
        changelog = os.path.join(changelog_dir, 'changelog-' + DATE + '.log')
        # export for sync
        os.putenv('EV_CHANGELOG', changelog)
        # sync the tree
        try:
            subprocess.check_call([os.path.join(HELPER_DIR, 'sync.sh')],
                    shell=True)
        except subprocess.CalledProcessError as e:
            logging.error('sync returned %d' % (e.returncode))
        # create the html changelog
        if os.path.exists(changelog):
            html_changelog = os.path.join(changelog_dir, 'changelog-' + DATE + '.html')
            cl = html.Create()
            cl.title('Changelog')
            cl.css('body {font-family:"Lucida Console", Monaco, monospace;}')
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

    # export vars for the build script
    os.putenv('NIGHTLY_BUILD', 'true')

    # for zip storage
    temp_dir = tempfile.mkdtemp()

    # keep track of builds
    build_start = datetime.now()

    # build each target
    for target in args.target:
        os.putenv('EV_BUILD_TARGET', target)
        # Run the build: target will be pulled from env
        if not args.nobuild:
            try:
                with open(os.path.join(temp_dir,'build_stderr'), 'w') as build_stderr:
                    target_start = datetime.now()
                    subprocess.check_call([os.path.join(
                            HELPER_DIR, 'build.sh')],
                            stdout=build_stderr, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                logging.error('Build returned %d for %s' % (e.returncode, target))
                handle_build_errors(os.path.join(temp_dir,'build_stderr'))
                continue
            else:
                logging.info('Built %s in %s' %
                        (target, pretty.time(datetime.now() - target_start)))
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
    logging.info('Built all targets in %s' %
            (pretty.time(datetime.now() - build_start)))

    # wait for builds to finish uploading/mirroring
    m_q.join()
    upq.join()

    # cleanup
    shutil.rmtree(temp_dir)

    logging.info('Total run time: %s' %
            (pretty.time(datetime.now() - script_start)))

    #
    # Finish up
    #

    # create html scriptlog
    if os.path.exists(scriptlog):
        html_scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.html')
        sl = html.Create()
        sl.title('Nightly Log')
        sl.css('body {font-family:"Lucida Console", Monaco, monospace;}')
        sl.header(DATE)
        sl.body(html.add_line_breaks(html.parse_file(scriptlog)))
        sl.write(html_scriptlog)
        # add log to rsync queues
        upq.put(html_scriptlog)
        m_q.put(scriptlog)
        # wait for complete
        m_q.join()
        upq.join()

    # run postupload script
    try:
        subprocess.check_call(['ssh', '%s@%s' % (droid_user,droid_host), 'test -e ~/android_scripts/updatewebsite.sh && cd ~/uploads/htdocs && ~/android_scripts/updatewebsite.sh'])
    except subprocess.CalledProcessError as e:
        logging.error('ssh returned %d while updating website' % (e.returncode))

    # cd previous working dir
    os.chdir(previous_working_dir)

if __name__ == "__main__":
    main(args)
