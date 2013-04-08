#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import argparse
from datetime import datetime
import logging
import os
import shutil
from subprocess import check_call
from subprocess import CalledProcessError as CPE
import Queue
import json

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
parser.add_argument('--port', help="Listen port for host sshd")
parser.add_argument('--user', help="Username for upload host")
parser.add_argument('--remotedir', help="Remote path for uploads")
parser.add_argument('--localdir', help="Local path for uploads")
parser.add_argument('--rebuild', help="Don't clobber before building",
                    action="store_false") # backwards
parser.add_argument('--nobuild', help=argparse.SUPPRESS,
                    action="store_true")
parser.add_argument('-q', '--quiet', help="Suppress all output",
                    action="store_true")
args = parser.parse_args()

# static vars
HELPER_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'helpers')
DATE = datetime.now().strftime('%Y.%m.%d')

def get_codename(target):
    codename = None
    for path,dirs,files in os.walk('device'):
        for d in dirs:
            if target == d:
                try:
                    f = open(os.path.join(path,d,'ev.mk'))
                except IOError:
                    continue
                else:
                    with f:
                        for line in f.readlines():
                            if 'PRODUCT_CODENAME' in line:
                                codename = line.rstrip('\n').split(' ')[2]
    return codename

def main(args):

    # script logging
    log_dir = os.path.join(args.source, 'release_logs')
    try:
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
    except OSError:
        pass
    scriptlog = os.path.join(log_dir, 'scriptlog-%s.log' % DATE)
    logging.basicConfig(filename=scriptlog,
                        format='%(levelname)-8s %(message)s',
                        level=logging.INFO,
                        )
    if not args.quiet:
        console = logging.StreamHandler()
        logging.getLogger('').addHandler(console)

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
    if not args.remotedir:
        droid_path = os.getenv('DROID_PATH')
    else:
        droid_path= args.remotedir
    if not args.localdir:
        droid_mirror = os.getenv('DROID_MIRROR')
        if not droid_mirror:
            droid_mirror = os.getenv('DROID_LOCAL_MIRROR')
    else:
        droid_mirror = args.localdir
    if not args.port:
        droid_host_port = os.getenv('DROID_HOST_PORT')
        if not droid_host_port:
            droid_host_port = '22'
    else:
        droid_host_port = args.port

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

    if uploading:
        # upload path
        upload_path = droid_path
        # upload thread
        upq = Queue.Queue()
        t1 = rsync.rsyncThread(upq, port=droid_host_port, message='Uploaded')
        t1.setDaemon(True)
        t1.start()

    if mirroring:
        # mirror path
        mirror_path = droid_mirror
        # mirror thread
        m_q = Queue.Queue()
        t2 = rsync.rsyncThread(m_q, message='Mirrored')
        t2.setDaemon(True)
        t2.start()

    #
    # Building
    #

    # for zip storage
    if os.path.isdir('/dev/shm'):
        temp_dir = '/dev/shm/tmp-releasebuilder_zips'
    else:
        temp_dir = '/tmp/tmp-releasebuilder_zips'
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
            if android.build(target,pkg,args.rebuild):
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
            codename = get_codename(target)
            if codename:
                if uploading:
                    # make the remote directories
                    try:
                        check_call(['ssh', '-p%s' % (droid_host_port),
                                '%s@%s' % (droid_user, droid_host),
                                'test -d %s || mkdir -p %s' % (os.path.join(upload_path,
                                codename),os.path.join(upload_path, codename))])
                    except CPE as e:
                        logging.error('ssh returned %d while making directories' %
                                (e.returncode))

                if mirroring:
                    try:
                        if not os.path.isdir(os.path.join(mirror_path, codename)):
                            os.makedirs(os.path.join(mirror_path, codename))
                    except OSError as e:
                        logging.error('failed to make mirror dir: %s' % (e))

                zip_info = []
                for z in zips:
                    zip_path = os.path.join(target_out_dir, z)
                    zip_info.append({
                            'date': DATE,
                            'device': target,
                            'count': 0,
                            'message': 'Release build for %s' % target,
                            'md5sum': md5sum(zip_path),
                            'name': z,
                            'size': os.path.getsize(zip_path),
                            'type': 'nightly',
                            'location': '%s/%s' % (codename,z),
                    })
                    shutil.copy2(zip_path,
                            os.path.join(temp_dir, z))
                    if uploading:
                        upq.put((os.path.join(temp_dir, z),
                                '%s@%s:%s' % (droid_user, droid_host,
                                os.path.join(upload_path, codename))))
                    if mirroring:
                        m_q.put((os.path.join(temp_dir, z),
                                os.path.join(mirror_path, codename)))
                json_info.append({
                        'codename': codename,
                        'zip_info': zip_info,
                })
            else:
                logging.error('Failed to get codename for %s' % (target))
        else:
            logging.warning('No zips found for %s' % target)

    # write total buildtime
    logging.info('Built all targets in %s' %
            (pretty_time(datetime.now() - build_start)))

    # wait for builds to finish uploading/mirroring
    if mirroring:
        m_q.join()
    if uploading:
        upq.join()

    if json_info and mirroring: # no uploading for now
        for entries in json_info:
            # Since builds are stored in the same directory
            # we have to read the old entries, add new ones, and rewrite
            device_manifest = os.path.join(mirror_path,
                              entries.get('codename'), 'info.json')
            device_entries = []
            try:
                f = open(device_manifest)
            except IOError as e:
                logging.error('%s' % e)
            else:
                with f:
                    device_entries = json.load(f)
            for e in entries.get('zip_info'):
                device_entries.append(e)
            try:
                f = open(device_manifest,'w')
            except IOError as e:
                logging.error('%s' % (e))
            else:
                with f:
                    json.dump(device_entries, f, indent=2)
        main_manifest = os.path.join(mirror_path,'manifest.json')
        try:
            f = open(main_manifest,'r')
        except IOError as e:
            logging.error('%s' % e)
        else:
            with f:
                main_entries = json.load(f)
            for entries in json_info:
                for e in entries.get('zip_info'):
                    main_entries.append(e)
            try:
                f = open(main_manifest,'w')
            except IOError as e:
                logging.error('%s' % e)
            else:
                with f:
                    json.dump(main_entries,f,indent=2)

    # cleanup
    shutil.rmtree(temp_dir)

    logging.info('Total run time: %s' %
            (pretty_time(datetime.now() - script_start)))

    # cd previous working dir
    os.chdir(previous_working_dir)

if __name__ == "__main__":
    main(args)
