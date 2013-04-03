# Andrew Sutherland <dr3wsuth3rland@gmail.com>

__all__ = [
    "md5sum",
    "pretty_time",
    "handle_build_errors",
]

import hashlib
import logging
import subprocess

def md5sum(filename):
    '''take string filename, returns hex md5sum as string'''
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()

def pretty_time(t):
    '''takes timedelta object, returns string'''
    h, r = divmod(t.seconds, 3600)
    m, s = divmod(r, 60)
    return '%sh %sm %ss' % (h, m, s)
