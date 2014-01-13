#!/usr/bin/env python
'''
    To be used for nightly builds to only keep the latest on the site
    arg 1: directory to check
    arg 2: directory to copy to
'''

from sys import argv
import os
import time
import shutil
import subprocess

#script, directory, backup_dir = argv
script,directory = argv

'''
try:
    print "backing up ",directory,"to ",backup_dir
    subprocess.check_call(['rsync', '-aq', directory, backup_dir])
except subprocess.CalledProcessError as e:
    print e
    exit()
'''

'''Yanked from stackoverflow
   delete subdirs in directories older than numdays
'''
numdays = 86400*15 # 2 weeks
now = time.time()
'''
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
'''

#Since nightlies are no longer built everyday we don't want to arbitrarily
#remove old dirs, in the off chance we don't commit anything for more
#than $maxdirs days, so instead we just remove the oldest dirs exceeding
#$maxdirs count
'''Sorts directories by mtime (newest first), then removes the oldest
   directories if count exceeds maxdirs
'''
maxdirs = 7
for root,dirs,files in os.walk(directory):
    lst = sorted(dirs, key=lambda d: os.path.getmtime(os.path.join(root,d)), reverse=True)
    for d in lst[maxdirs:]:
        print "removing", os.path.join(root,d)
        shutil.rmtree(os.path.join(root,d))
    break # only want first level

