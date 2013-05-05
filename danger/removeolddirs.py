#!/usr/bin/env python
'''
    Yanked from stackoverflow
    delete subdirs in directories older than numdays
    backs up diretory first
    To be used for nightly builds to only keep the latest on the site
    arg 1: directory to check
    arg 2: directory to copy to
'''

from sys import argv
import os
import time
import shutil

numdays = 86400*22 # 3 weeks
now = time.time()
script, directory, backup_dir = argv

try:
    subprocess.check_call(['rsync', '-aq', directory, backup_dir])
except subprocess.CalledProcessError as e:
    print e
    exit()

for r,d,f in os.walk(directory):
    for dir in d:
         timestamp = os.path.getmtime(os.path.join(r,dir))
         if now - numdays > timestamp:
             try:
                  print "removing ",os.path.join(r,dir)
                  shutil.rmtree(os.path.join(r,dir))
             except Exception as e:
                  print e
                  pass
