# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os
import logging
from multiprocessing import cpu_count
from subprocess import check_call, check_output, STDOUT
from subprocess import CalledProcessError as CPE
from tempfile import mkdtemp
from shutil import rmtree

__all__ = [
    "build",
    "reposync",
    "get_changelog",
]

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
    load = num_cpus * 2.5

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

def reposync():
    cmds = {
        'sync':     ('repo', 'sync', '-fdq', '-j12'),
        'gitclean': ('repo', 'forall', '-c', 'git', 'clean', '-fdq'),
        'gitreset': ('repo', 'forall', '-c', 'git', 'reset', '-q', '--hard'),
        'status':   ('repo', 'status', '-j4'),
    }
    count = 0
    retries = 2
    failed = False
    while count < retries:
        try:
            with open(os.devnull,'w') as out:
                check_call(cmds.get('sync'),stdout=out,stderr=STDOUT)
        except CPE as e:
            failed = True
            logging.error(e)
        else:
            failed = False
            break
        count += 1
    if failed:
        try:
            logging.error('Attempting to fix the repo')
            check_call(cmds.get('gitclean'))
            check_call(cmds.get('gitreset'))
            with open(os.devnull,'w') as out:
                check_call(cmds.get('sync'),stdout=out,stderr=STDOUT)
        except CPE as e:
            logging.error(e)
        else:
            failed = False
    if failed:
        try:
            logging.error('Looks like the repo is fucked up, dumping status:')
            logging.error(check_output(cmds.get('status')))
        except CPE as e:
            logging.error(e)
    return failed

def _update_branch(new):
    try:
        with open(os.devnull,'w') as out:
            check_call(('repo','start','%s' % new, '--all'),stdout=out,stderr=STDOUT)
    except CPE as e:
        logging.error(e)
    else:
        try:
            f = open('.previous_branch','w')
        except IOError as e:
            logging.error(e)
        else:
            with f:
                f.write(new)
            logging.info("Set %s as current branch" % new)
    return

def get_changelog(current,changelog):
    try: # read the previous branch
        f = open('.previous_branch')
    except IOError as e:
        logging.error(e)
        # It probably doesn't exist. Initialize it
        _update_branch(current)
    else:
        with f:
            previous = f.readline().rstrip('\n')
        _update_branch(current)
        try: # Write the changelog
            with open(changelog,'w') as out:
                out.write('%s..%s\n' % (previous,current))
            with open(changelog,'a') as out, open(os.devnull,'w') as err:
                check_call(('repo','forall','-pvc','git','log','--oneline',
                    '--no-merges','%s..%s' % (previous,current)),
                    stdout=out, stderr=err)
        except CPE as e:
            logging.error(e)
        try: # Detach the tree
            with open(os.devnull,'w') as out:
                check_call(('repo','sync','-fdlq','-j12'),stdout=out,stderr=STDOUT)
        except CPE as e:
            logging.error(e)
    return
