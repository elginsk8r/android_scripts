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
from drewis import rsync, pretty

VERSION = '0.1'

# handle commandline args
parser = argparse.ArgumentParser(description="Drew's builder script")
parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
parser.add_argument('target', help="Device(s) to build",
                    nargs='+')
parser.add_argument('--source', help="Path to android tree",
                    default=os.getcwd())
parser.add_argument('--host', help="Hostname for upload")
parser.add_argument('--port', help="Listen port for host sshd")
parser.add_argument('--user', help="Username for upload host")
parser.add_argument('--mirror', help="Path for upload mirroring")
parser.add_argument('--nobuild', help=argparse.SUPPRESS,
                    action="store_true")
args = parser.parse_args()

# static vars
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'release')
DATE = datetime.now().strftime('%Y.%m.%d')

# script logging
log_dir = os.path.join(args.source, 'release_logs')
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)
scriptlog = os.path.join(log_dir, 'scriptlog-' + DATE + '.log')
logging.basicConfig(filename=scriptlog, level=logging.INFO,
        format='%(levelname)s:%(message)s')

def get_codename(target):
    codename = None
    for p,d,f in os.walk('device'):
        for dirs in d:
            if target in dirs:
                with open(os.path.join(p,dirs,'ev.mk')) as f:
                    contents = f.read().split('\n')
                    for line in contents:
                        if 'PRODUCT_CODENAME' in line:
                            codename = line.split(' ')[2]
    return codename

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
    if not args.port:
        droid_host_port = os.getenv('DROID_HOST_PORT')
        if not droid_host_port:
            droid_host_port = '22'
    else:
        droid_host_port = args.port

    # these vars are mandatory
    if not droid_host or not droid_user or not local_mirror:
        print 'DROID_HOST or DROID_USER or DROID_LOCAL_MIRROR not set... Bailing'
        exit()

    # cd working dir
    previous_working_dir = os.getcwd()
    os.chdir(args.source)

    # upload path
    upload_path = os.path.join('~', 'uploads')

    # mirror path
    mirror_path = local_mirror

    # upload thread
    upq = Queue.Queue()
    t1 = rsync.rsyncThread(upq, port=droid_host_port, message='Uploaded')
    t1.setDaemon(True)
    t1.start()

    # mirror thread
    m_q = Queue.Queue()
    t2 = rsync.rsyncThread(m_q, message='Mirrored')
    t2.setDaemon(True)
    t2.start()

    #
    # Building
    #

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
                with open(os.devnull, 'w') as shadup:
                    target_start = datetime.now()
                    subprocess.check_call([os.path.join(SCRIPT_DIR, 'build.sh')],
                            stdout=shadup, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                logging.error('Build returned %d for %s' % (e.returncode, target))
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
            codename = get_codename(target)
            if codename:
                # make the remote directories
                try:
                    subprocess.check_call(['ssh', '-p%s' % (droid_host_port),
                            '%s@%s' % (droid_user, droid_host),
                            'test -d %s || mkdir -p %s' % (os.path.join(upload_path,
                            codename),os.path.join(upload_path, codename))])
                except subprocess.CalledProcessError as e:
                    logging.error('ssh returned %d while making directories' %
                            (e.returncode))
                    continue

                if not os.path.isdir(os.path.join(mirror_path, codename)):
                    os.makedirs(os.path.join(mirror_path, codename))

                for z in zips:
                    shutil.copy(os.path.join(target_out_dir, z),
                            os.path.join(temp_dir, z))
                    upq.put((os.path.join(temp_dir, z),
                            '%s@%s:%s' % (droid_user, droid_host,
                            os.path.join(upload_path, codename))))
                    m_q.put((os.path.join(temp_dir, z),
                            os.path.join(mirror_path, codename)))
            else:
                logging.error('Failed to get codename for %s' % (target))
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

    # cd previous working dir
    os.chdir(previous_working_dir)

if __name__ == "__main__":
    main(args)