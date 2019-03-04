# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os
import logging
import threading
import traceback
from subprocess import check_call, check_output, STDOUT, Popen
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
    '''Returns true on failure'''
    failed = False
    try:
        with open('/proc/meminfo') as f:
            mem_total = f.readline().split()[1]
    except IOError:
        mem_total = 8199922 # 8GB

    jobs = int((int(mem_total)*0.7)/1000000) # 70% available ram
    jobs += jobs % 2 # ensure even number
    max_jobs = 32 # Testing shows more than 32 jobs does not improve build times
    if jobs > max_jobs:
        jobs = max_jobs

    cmds = {
        'clobber': ('make','clobber'),
        'installclean': ('make','installclean'),
        'build': "source build/envsetup.sh && lunch %s && make -j%d %s" %(target,jobs,packages)
    }

    try:
        with open(os.devnull,'w') as out:
            if clobber:
                check_call(cmds.get('clobber'), stdout=out, stderr=STDOUT)
            else:
                check_call(cmds.get('installclean'), stdout=out, stderr=STDOUT)
    except CPE as e:
        logging.error(e)

    tempd = mkdtemp() # I dont understand mkstemp
    tempf = os.path.join(tempd,'buildout')
    build_thread = CommandThread(cmds.get('build'))
    try:
        with open(tempf,'w') as err, open(os.devnull,'w') as out:
            # Give builds 90 mins to complete, if they haven't finished by then
            # something is wrong and they need to be killed
            build_status, build_error = build_thread.run(timeout=None,
                                                stdout=out, stderr=err,
                                                shell=True, executable='/bin/bash')
    except IOError:
        failed = True
    if build_status != 0:
        logging.error('FAILED: %s, %s' % (cmds.get('build'),build_error))
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
            #failed = True
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
    has_changes = True
    try: # read the previous branch
        f = open('.previous_branch')
    except IOError as e:
        logging.warning(e)
        # It probably doesn't exist. Initialize it
        _update_branch(current)
    else:
        with f:
            previous = f.readline().rstrip('\n')
        _update_branch(current)
        try: # Get the changelog
            tempd = mkdtemp()
            temp_changelog = os.path.join(tempd,'temp_changelog')
            with open(temp_changelog,'w') as out, open(os.devnull,'w') as err:
                check_call(('repo','forall','-pvc','git','log','--oneline',
                    '--no-merges','%s..%s' % (previous,current)),
                    stdout=out, stderr=err)
        except CPE as e:
            logging.error(e)
        finally: # Write the changelog
            if os.path.getsize(temp_changelog) == 0:
                with open(temp_changelog,'w') as out:
                    out.write("No new commits found.\n")
                has_changes = False
            with open(changelog,'w') as outfile, open(temp_changelog) as infile:
                outfile.write('%s..%s\n' % (previous,current))
                for line in infile:
                    outfile.write(line)
            rmtree(tempd)
        try: # Detach the tree
            with open(os.devnull,'w') as out:
                check_call(('repo','sync','-fdlq','-j12'),stdout=out,stderr=STDOUT)
        except CPE as e:
            logging.error(e)
    return has_changes

class CommandThread(object):
    """
    Enables to run subprocess commands in a different thread with TIMEOUT option.

    Based on kirpits improvement https://gist.github.com/kirpit/1306188
    of jcollado's solution:
    http://stackoverflow.com/questions/1191374/subprocess-with-timeout/4825933#4825933
    """
    command = None
    process = None
    status = None
    output, error = '', ''

    def __init__(self, command):
        self.command = command

    def run(self, timeout=None, **kwargs):
        """ Run a command then return: (status, error, output). """
        def target(**kwargs):
            try:
                self.process = Popen(self.command, **kwargs)
                self.output, self.error = self.process.communicate()
                self.status = self.process.returncode
            except:
                self.error = traceback.format_exc()
                self.status = -1
        # thread
        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
        return self.status, self.error #self.output
