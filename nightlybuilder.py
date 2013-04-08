#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import argparse
from datetime import datetime
import json
import logging
import os
import shutil
import subprocess
import Queue

# local
from drewis import __version__
from drewis import html,rsync,android
from drewis.utils import *

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
parser.add_argument('target', help="Device(s) to build",
                    nargs='+')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
parser.add_argument('--host', help="Hostname for upload")
parser.add_argument('--user', help="Username for upload host")
parser.add_argument('--remotedir', help="Remote path for uploads")
parser.add_argument('--localdir', help="Local path for uploads")
parser.add_argument('--nosync', help=argparse.SUPPRESS,
                    action="store_true")
parser.add_argument('--nobuild', help=argparse.SUPPRESS,
                    action="store_true")
args = parser.parse_args()

# static vars
HELPER_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'helpers')
DATE = datetime.now().strftime('%Y.%m.%d')

def main(args):

    # script logging
    log_dir = os.path.join(args.source, 'nightly_logs')
    try:
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
    except OSError:
        pass
    scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.log')
    logging.basicConfig(filename=scriptlog, level=logging.INFO,
            format='%(levelname)-8s %(message)s')

    # for total runtime
    script_start = datetime.now()

    logging.info(script_start)

    # set vars for uploading/mirroring
    if not args.user:
        droid_user = os.getenv('DROID_USER')
    else:
        droid_user = args.user
    if not args.host:
        droid_host = os.getenv('DROID_HOST')
    else:
        droid_host = args.host
    if not args.remotedir:
        droid_path = os.getenv('DROID_PATH')
    else:
        droid_path = args.remotedir
    if not args.localdir:
        droid_mirror = os.getenv('DROID_MIRROR')
        if not droid_mirror:
            droid_mirror = os.getenv('DROID_LOCAL_MIRROR')
    else:
        droid_mirror = args.localdir

    # we must put the builds somewhere
    if not droid_mirror:
        mirroring = False
        if droid_host and droid_user and droid_path:
            uploading = True
        else:
            logging.error('DROID_MIRROR not set')
            logging.error('DROID_HOST or DROID_USER or DROID_PATH not set')
            logging.error('no where put builds. BAILING!!')
            exit()
    else:
        mirroring = True
        if droid_host and droid_user and droid_path:
            uploading = True
        else:
            uploading = False

    # cd working dir
    previous_working_dir = os.getcwd()
    os.chdir(args.source)

    # we want group write
    os.umask(002)

    # make the remote directories
    if uploading:
        upload_path = os.path.join(droid_path, DATE)
        try:
            subprocess.check_call(['ssh', '%s@%s' % (droid_user, droid_host),
                    'test -d %s || mkdir -p %s' % (upload_path,upload_path)])
        except subprocess.CalledProcessError as e:
            logging.error('ssh returned %d while making directories' %
                    (e.returncode))
            uploading = False
            if not mirroring:
                logging.error('no where to put builds. BAILING!!')
                exit()
        else:
            # upload thread
            upq = Queue.Queue()
            t1 = rsync.rsyncThread(upq,
                    '%s@%s:%s' % (droid_user, droid_host, upload_path),
                    message='Uploaded')
            t1.setDaemon(True)
            t1.start()

    if mirroring:
        mirror_path = os.path.join(droid_mirror, DATE)
        try:
            if not os.path.isdir(mirror_path):
                os.makedirs(mirror_path)
                subprocess.call(['chmod','775','%s' % (mirror_path)])
        except OSError as e:
            logging.error('failed to make mirror dir: %s' % (e))
            mirroring = False
            if not uploading:
                logging.error('no where to put builds. BAILING!!')
                exit()
        else:
            # mirror thread
            m_q = Queue.Queue()
            t2 = rsync.rsyncThread(m_q,
                    mirror_path,
                    message='Copied')
            t2.setDaemon(True)
            t2.start()

    #
    # Syncing
    #

    if not args.nosync:
        # common directory for all changelogs
        changelog_dir = os.path.join(os.path.realpath(os.getcwd()), 'nightly_changelogs')
        try:
            if not os.path.isdir(changelog_dir):
                os.mkdir(changelog_dir)
        except OSError:
            pass
        # changelog
        changelog = os.path.join(changelog_dir, 'changelog-' + DATE + '.log')
        # sync the tree
        if android.reposync():
            logging.error('Sync failed. Skipping the build')
            args.nobuild = True
            # Remove out so we dont upload yesterdays build
            if os.path.isdir('out'):
                shutil.rmtree('out')
        else:
            android.get_changelog(DATE,changelog)

        # create the html changelog
        if os.path.exists(changelog):
            logging.info('Created changelog for %s' % DATE)
            html_changelog = os.path.join(changelog_dir, 'changelog-' + DATE + '.html')
            cl = html.Create()
            cl.title('Changelog')
            cl.css('body {font-family:"Lucida Console", Monaco, monospace;font-size:0.9em;}')
            clbody = html.parse_file(changelog)
            cl.header(clbody[0])
            cl.body(html.add_line_breaks(clbody[1:]))
            cl.write(html_changelog)
            # add changelog to rsync queues
            if uploading:
                upq.put(html_changelog)
            if mirroring:
                m_q.put(html_changelog)
    else:
        logging.info('Skipped sync')

    #
    # Building
    #

    # export vars for the build script
    os.putenv('NIGHTLY_BUILD', 'true')

    # for zip storage
    if os.path.isdir('/dev/shm'):
        temp_dir = '/dev/shm/tmp-nightlybuilder_zips'
    else:
        temp_dir = '/tmp/tmp-nightlybuilder_zips'
    if not os.path.isdir(temp_dir):
        os.mkdir(temp_dir)

    # keep track of builds
    build_start = datetime.now()

    # for json manifest
    json_info = []

    # build each target
    for target in args.target:
        if not args.nobuild:
            target_start = datetime.now()
            pkg = 'otapackage'
            if target == 'passion':
                pkg = 'otapackage systemupdatepackage'
            if android.build(target,pkg):
                continue # Failed
            else:
                logging.info('Built %s in %s' %
                        (target, pretty_time(datetime.now() - target_start)))
        # find and add the zips to the rsync queues
        zips = []
        target_out_dir = os.path.join('out', 'target', 'product', target)
        if os.path.isdir(target_out_dir):
            for f in os.listdir(target_out_dir):
                if f.startswith('ev') and f.endswith('.zip'):
                    zips.append(f)
        if zips:
            for z in zips:
                json_info.append({
                        'date': DATE,
                        'device': target,
                        'count': 0,
                        'message': 'Nightly build for %s' % target,
                        'md5sum': md5sum(os.path.join(target_out_dir, z)),
                        'name': z,
                        'size': os.path.getsize(os.path.join(target_out_dir, z)),
                        'type': 'nightly',
                        'location': '%s/%s' % (DATE,z),
                })
                shutil.copy2(os.path.join(target_out_dir, z),os.path.join(temp_dir, z))
                if uploading:
                    upq.put(os.path.join(temp_dir, z))
                if mirroring:
                    m_q.put(os.path.join(temp_dir, z))
        else:
            logging.warning('No zips found for %s' % target)

    # write total buildtime
    logging.info('Built all targets in %s' %
            (pretty_time(datetime.now() - build_start)))

    # write manifest
    if json_info:
        json_info.sort(key=lambda d:d['device'])
        try:
            f = open(os.path.join(temp_dir,'info.json'),'w')
        except IOError as e:
            logging.error('Failed to open info.json: %s' % (e))
        else:
            with f:
                json.dump(json_info, f, indent=2)
            if uploading:
                upq.put(os.path.join(temp_dir,'info.json'))
            if mirroring:
                m_q.put(os.path.join(temp_dir,'info.json'))
        # for website
        if mirroring:
            main_manifest = os.path.join(droid_mirror,'manifest.json')
            try:
                f = open(main_manifest,'r')
            except IOError as e:
                logging.error('Failed to open %s: %s' % (main_manifest,e))
            else:
                with f:
                    entries = json.load(f)
                for e in json_info:
                    entries.append(e)
                try:
                    f = open(main_manifest,'w')
                except IOError as e:
                    logging.error('Failed to open %s: %s' % (main_manifest,e))
                else:
                    with f:
                        json.dump(entries,f,indent=2)


    # wait for builds to finish uploading/mirroring
    if mirroring:
        m_q.join()
    if uploading:
        upq.join()

    # cleanup
    shutil.rmtree(temp_dir)

    logging.info('Total run time: %s' %
            (pretty_time(datetime.now() - script_start)))

    #
    # Finish up
    #

    # create html scriptlog
    if os.path.exists(scriptlog):
        html_scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.html')
        sl = html.Create()
        sl.title('Nightly Log')
        sl.css('body {font-family:"Lucida Console", Monaco, monospace;font-size:0.9em;}')
        sl.header(DATE)
        sl.body(html.add_line_breaks(html.parse_file(scriptlog)))
        sl.write(html_scriptlog)
        # add log to rsync queues
        if uploading:
            upq.put(html_scriptlog)
            upq.join()
        if mirroring:
            m_q.put(html_scriptlog)
            m_q.join()

    # cd previous working dir
    os.chdir(previous_working_dir)

if __name__ == "__main__":
    main(args)
