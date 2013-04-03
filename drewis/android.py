# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os
import logging
from multiprocessing import cpu_count
from subprocess import check_call, check_output
from subprocess import CalledProcessError as CPE
from tempfile import mkdtemp
from shutil import rmtree

def _log_build_errors(error_file):
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
                    errors = check_output(grepcmd[1], stdin=f)
                except CPE as e:
                    pass # Raised if grep doesn't find any matches
                else:
                    if errors:
                        logging.error(grepcmd[0])
                        for line in errors.split('\n'):
                            logging.error(line)
                f.seek(0)
            logging.error('Hopefully that helps')
    except IOError as e:
        logging.error('Error opening %s: %s' % (error_file,e))

def build(target, packages, clobber=True):
    failed = False
    cmds = {
        'clobber': ('make','clobber'),
    }
    num_cpus = cpu_count()
    load = num_cpus * 1.5 # Don't hose the build server (its used for other things too)

    if clobber:
        try:
            check_call(cmds.get('clobber'))
        except CPE as e:
            logging.error(e)

    tempd = mkdtemp() # I dont understand mkstemp
    tempf = os.path.join(tempd,'buildout')
    try:
        with open(tempf,'w') as err, open(os.devnull,'w') as out:
            # This is ugly and /very/ bad way to do this,
            # But I would rather have it this way than calling a script to run
            # these commands. So if the parent script is killed, make doesnt
            # continue running in the background
            check_call("source build/envsetup.sh; breakfast %s;make -j -l%d %s" %
                          (target,load,packages), stdout=out, stderr=err, shell=True)
    except IOError:
        pass
        failed = True
    except CPE as e:
        logging.error(e)
        _log_build_errors(tempf)
        failed = True
    rmtree(tempd)
    return failed
