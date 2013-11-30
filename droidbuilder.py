#!/usr/bin/env python2
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

# static vars
DATE = datetime.now().strftime('%Y.%m.%d')
# globals
BUILD_TYPE = None
TESTING_BUILD = False
RELEASE_BUILD = False
NIGHTLY_BUILD = False
#TODO remove from global
REBUILD = False

def handle_args():
    parser = argparse.ArgumentParser(
            description="Build and upload android",
            epilog="This script is designed to allow you to effortlessly build and publish android builds. A key feature being, it will automatically create/update the info.json files in the build directories (for local only).",
            )
    parser.add_argument('--version', action="version", version="%(prog)s " + __version__)

    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument('target',
            help="device(s) to build",
            nargs='+',
            )

    build_options = common_options.add_argument_group("building")
    build_options.add_argument('--source',
            help="path to android tree (default pwd)",
            default=os.getcwd(),
            )

    upload_options = common_options.add_argument_group("uploading")
    upload_options.add_argument('--host',
            help="hostname",
            )
    upload_options.add_argument('--user',
            help="username for host",
            )
    upload_options.add_argument('--remotedir',
            help="common remote path (device dirs added automatically)",
            )
    upload_options.add_argument('--port',
            help="ssh port (default 22)",
            )

    mirror_options = common_options.add_argument_group("mirroring")
    mirror_options.add_argument('--localdir',
            help="common local path (device dirs added automatically)",
            )

    debug_options = common_options.add_argument_group("debugging")
    debug_options.add_argument('--nobuild',
            help="",
            action="store_true",
            )

    release_testing_options = argparse.ArgumentParser(add_help=False)
    release_testing_options.add_argument('-q','--quiet',
            help="don't log to console",
            action="store_true",
            )
    release_testing_options.add_argument('--message',
            help="note to put in 'message' field in info",
            )

    build_options2 = release_testing_options.add_argument_group("building")
    build_options2.add_argument('--rebuild',
            help="don't clobber before building",
            action="store_true",
            )

    nightly_options = argparse.ArgumentParser(add_help=False)

    debug_options2 = nightly_options.add_argument_group("debugging")
    debug_options2.add_argument('--nosync',
            help="",
            action="store_true",
            )

    subcommands = parser.add_subparsers(
            title='subcommands',
            )
    testing = subcommands.add_parser("testing",
            parents=[common_options,release_testing_options],
            help="testing builds",
            )
    testing.set_defaults(func=testing_build)
    release = subcommands.add_parser("release",
            parents=[common_options,release_testing_options],
            help="release builds",
            )
    release.set_defaults(func=release_build)
    nightly = subcommands.add_parser("nightly",
            parents=[common_options,nightly_options],
            help="nightly builds",
            )
    nightly.set_defaults(func=nightly_build)

    return parser.parse_args()

def setup_logging(directory,verbose=False):
    try:
        if not os.path.isdir(directory):
            os.makedirs(directory)
    except OSError:
        pass # TODO
    else:
        scriptlog = os.path.join(directory, "scriptlog-%s.log" % DATE)
        logging.basicConfig(filename=scriptlog,
                level=logging.INFO,
                format='%(levelname)-8s %(message)s'
                )
        if verbose:
            console = logging.StreamHandler()
            logging.getLogger('').addHandler(console)

def get_codename(target):
    if NIGHTLY_BUILD:
        return DATE
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

def get_message(target,args):
    if not NIGHTLY_BUILD:
        if args.message:
            return args.message
    return "%s build for %s" % (BUILD_TYPE,target)

def testing_build(args):
    global BUILD_TYPE
    BUILD_TYPE = 'testing'
    global TESTING_BUILD
    TESTING_BUILD = True
    global REBUILD
    REBUILD = args.rebuild
    setup_logging(os.path.join(args.source,'testing_logs'), not args.quiet)
    main(args)

def release_build(args):
    global BUILD_TYPE
    BUILD_TYPE = 'release'
    global RELEASE_BUILD
    RELEASE_BUILD = True
    global REBUILD
    REBUILD = args.rebuild
    setup_logging(os.path.join(args.source,'release_logs'), not args.quiet)
    main(args)

def nightly_build(args):
    global BUILD_TYPE
    BUILD_TYPE = 'nightly'
    global NIGHTLY_BUILD
    NIGHTLY_BUILD = True
    setup_logging(os.path.join(args.source,'nightly_logs'))
    main(args)

def main(args):
    logging.info("Starting %s build" % BUILD_TYPE)
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

    uploading = False
    if droid_host and droid_user and droid_path:
        uploading = True

    mirroring = False
    if droid_mirror:
        mirroring = True

    # we must put the builds somewhere
    if not mirroring and not uploading:
        logging.error("DROID_MIRROR not set")
        logging.error("DROID_HOST or DROID_USER or DROID_PATH not set")
        logging.error("no where put builds. BAILING!!")
        exit()

    # cd working dir
    previous_working_dir = os.getcwd()
    os.chdir(args.source)

    if uploading:
        upload_path = droid_path
        # upload thread
        upq = Queue.Queue()
        t1 = rsync.rsyncThread(upq, port=droid_host_port, message='Uploaded')
        t1.setDaemon(True)
        t1.start()

    if mirroring:
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
    if os.path.isdir("/dev/shm"):
        temp_dir = "/dev/shm/tmp-%s-droidbuilder_zips" % os.getenv("USER")
    else:
        temp_dir = "/tmp/tmp-%s-droidbuilder_zips" % os.getenv("USER")
    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)

    # keep track of builds
    build_start = datetime.now()

    # for json manifest
    json_info = []

    # Targets to run through the squisher
    squisher_targets = (
            'passion',
            'bravo',
            'supersonic',
            'inc',
            'speedy',
    )

    # Export the proper build type
    if TESTING_BUILD:
        os.putenv('TESTING_BUILD','true')
        os.putenv('RELEASE_BUILD','false')
        os.putenv('NIGHTLY_BUILD','false')
    elif RELEASE_BUILD:
        os.putenv('TESTING_BUILD','false')
        os.putenv('RELEASE_BUILD','true')
        os.putenv('NIGHTLY_BUILD','false')
    elif NIGHTLY_BUILD:
        os.putenv('TESTING_BUILD','false')
        os.putenv('RELEASE_BUILD','false')
        os.putenv('NIGHTLY_BUILD','true')

    # build each target
    for target in args.target:
        if not args.nobuild:
            target_start = datetime.now()
            pkg = 'otapackage'
            if target in squisher_targets:
                pkg = 'squishedpackage'
            if android.build(target,pkg,not REBUILD):
                continue # Failed #TODO reverse return value
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
            # testing and release builds are put in codename subdirs
            # nightly will just be DATE
            codename = get_codename(target)
            if codename:
                if uploading:
                    # make the remote directories
                    full_upload_path = os.path.join(upload_path, codename)
                    try:
                        subprocess.check_call(('ssh',
                            '-p%s' % (droid_host_port),
                            '%s@%s' % (droid_user, droid_host),
                            'test -d %s || mkdir -p %s' %
                                (full_upload_path, full_upload_path)
                            ))
                    except subprocess.CalledProcessError as e:
                        logging.error('ssh returned %d while making %s' %
                                (e.returncode, full_upload_path))
                        if not mirroring:
                            continue

                if mirroring:
                    full_mirror_path = os.path.join(mirror_path, codename)
                    try:
                        if not os.path.isdir(full_mirror_path):
                            os.makedirs(full_mirror_path)
                    except OSError as e:
                        logging.error(e)
                        continue

                zip_info = []
                for z in zips:
                    zip_path = os.path.join(target_out_dir, z)
                    temp_zip_path = os.path.join(temp_dir, z)
                    zip_info.append({
                            'date': DATE,
                            'device': target,
                            'count': 0,
                            'message': get_message(target,args),
                            'md5sum': md5sum(zip_path),
                            'name': z,
                            'size': os.path.getsize(zip_path),
                            'type': BUILD_TYPE,
                            'location': '%s/%s' % (codename,z),
                    })
                    shutil.copy2(zip_path, temp_zip_path)
                    if uploading:
                        upq.put((temp_zip_path,
                            '%s@%s:%s' % (droid_user, droid_host, full_upload_path)
                            ))
                    if mirroring:
                        m_q.put((temp_zip_path,
                            full_mirror_path
                            ))
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

    if json_info and mirroring: # TODO uploading
        for entries in json_info:
            # Release and testing builds are stored in the same directory,
            # so we have to read the old entries, add new ones, and rewrite
            # Nightly wont have one initially and all builds are
            # stored in the same directory so it will just re(read/write)
            # for all builds which is stupid but will work fine
            device_manifest = os.path.join(mirror_path,
                              entries.get('codename'), 'info.json')
            device_entries = []
            try:
                f = open(device_manifest)
            except IOError as e:
                pass #logging.error('%s' % e)
            else:
                with f:
                    device_entries = json.load(f)
            for e in entries.get('zip_info'):
                device_entries.append(e)
            try:
                f = open(device_manifest,'w')
            except IOError as e:
                logging.error(e)
            else:
                with f:
                    json.dump(device_entries, f, indent=2)

    # cleanup
    shutil.rmtree(temp_dir)

    logging.info('Total run time: %s' %
            (pretty_time(datetime.now() - script_start)))

    # cd previous working dir
    os.chdir(previous_working_dir)


if __name__ == "__main__":
    args = handle_args()
    args.func(args)

