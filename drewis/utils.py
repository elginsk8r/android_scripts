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

def handle_build_errors(error_file):
    grepcmds = [
        ('GCC:', ('grep', '-B 1', '-A 2', '-e error:')),
        ('JAVA:', ('grep', '-B 10', '-e error$')), # combine these someday
        ('JAVA:', ('grep', '-B 20', '-e errors$')),
        ('MAKE:', ('grep', '-e \*\*\*\ '))] # No idea why ^make won't work
    try:
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
    except IOError as e:
        logging.error('Error opening %s: %s' % (error_file,e))
