#!/usr/bin/env python
'''
    Yanked from stackoverflow
    delete subdirs in directories older than numdays
    To be used for nightly builds to only keep the latest
    arg 1: directory to check
'''

from sys import argv
import os
import time
import shutil

numdays = 86400*14 # 2 weeks
now = time.time()
script, directory = argv
for r,d,f in os.walk(directory):
    for dir in d:
         timestamp = os.path.getmtime(os.path.join(r,dir))
         if now - numdays > timestamp:
             try:
                  print "removing ",os.path.join(r,dir)
                  shutil.rmtree(os.path.join(r,dir))
             except Exception,e:
                  print e
                  pass
