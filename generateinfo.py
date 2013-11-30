#!/usr/bin/env python2

from datetime import datetime
import hashlib
from zipfile import ZipFile
import tempfile
import os
import json
from sys import argv
import argparse

# local
from drewis import __version__

def handle_args():
    parser = argparse.ArgumentParser(
            description="Generate and update build manifests",
            epilog="Run this against your releases/testing directories to add new builds to the website's manifest.",
            )
    parser.add_argument('--version', action="version", version="%(prog)s " + __version__)

    common_options = argparse.ArgumentParser(add_help=False)
    common_options.add_argument('directory',
            help="Directory to scan and update manifest in",
            )
    common_options.add_argument('--message',
            help="Custom message to display as changelog",
            default=None,
            )

    subcommands = parser.add_subparsers(
            title='subcommands',
            )
    testing = subcommands.add_parser("testing",
            parents=[common_options],
            help="testing builds",
            )
    testing.set_defaults(func=testing_build)
    release = subcommands.add_parser("release",
            parents=[common_options],
            help="release builds",
            )
    release.set_defaults(func=release_build)
    gapps = subcommands.add_parser("gapps",
            parents=[common_options],
            help="gapps zips",
            )
    gapps.set_defaults(func=gapps_zip)

    return parser.parse_args()

def testing_build(args):
    main('testing',args.directory,args.message)

def release_build(args):
    main('release',args.directory,args.message)

def gapps_zip(args):
    main('gapps',args.directory,args.message)

def date_from_stamp(stamp):
    t = datetime.utcfromtimestamp(stamp)
    return t.strftime('%Y.%m.%d')

def md5sum(filename):
    '''take string filename, returns hex md5sum as string'''
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()

def handle_zips(build_type,walk_dir,message,current_builds=None):
    json_info = []
    for path,dirs,files in os.walk(walk_dir):
        for f in files:
            if f.endswith('.zip') and not f.endswith('fastboot-update.zip'):
                if current_builds is not None:
                    if f in current_builds:
                        print "Found existing build %s" % f
                        continue
                    else:
                        print "Found new build %s" % f
                p = os.path.join(path,f)
                date = None
                target = None
                if build_type == 'gapps':
                    # We hack together the date from the filename
                    rawdate = list(f.split('-')[2])
                    rawdate.insert(6,'.')
                    rawdate.insert(4,'.')
                    date = "".join(rawdate)
                    target = 'gapps'
                else:
                    with ZipFile(p,'r') as z:
                        try:
                            bp = z.open('system/build.prop')
                            props = bp.readlines()
                            for prop in props:
                                if prop.startswith("ro.build.date.utc"):
                                    date = date_from_stamp(int(prop.split('=')[1].strip()))
                                if prop.startswith("ro.product.device"):
                                    target = prop.split('=')[1].strip()
                        except KeyError:
                            print "FATAL: unable to open zip %s for reading" % f
                            exit()
                if target is None or date is None:
                    print "FATAL: null target or date"
                    exit()
                md5 = md5sum(p)
                size = os.path.getsize(p)
                cname = os.path.basename(path.rstrip('/'))
                if message is None:
                    message = "%s build for %s" % (build_type, target)
                json_info.append({
                            'date': date,
                            'device': target,
                            'count': 0,
                            'message': message,
                            'md5sum': md5,
                            'name': f,
                            'size': size,
                            'type': build_type,
                            'location': '%s/%s' %(cname,f),
                })
    return json_info

def main(build_type,walk_dir,message):
    json_info = []
    device_manifest = os.path.join(walk_dir,'info.json')
    device_entries = []
    try:
        f = open(device_manifest)
    except IOError as e:
        pass
    else:
        with f:
            device_entries = json.load(f)
    if device_entries:
        current_builds = []
        for e in device_entries:
            current_builds.append(e.get('name'))
        device_entries.extend(handle_zips(build_type,walk_dir,message,current_builds))
    else:
        device_entries = handle_zips(build_type,walk_dir,message)

    try:
        f = open(device_manifest,'w')
    except IOError as e:
        print "FATAL: unable to open info.json for writing"
        exit()
    else:
        with f:
            device_entries.sort(key=lambda d:d['date'])
            json.dump(device_entries, f, indent=2)

if __name__ == "__main__":
    args = handle_args()
    if args.directory == '.':
        print "FATAL: I can't be run from the current directory. Move up one"
        exit()
    args.func(args)

