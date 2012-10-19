#!/bin/bash

# update mirror
#rsync -rtP -e 'ssh -p30000' evervolv@217.150.244.124:~/uploads/ /home/drew/uploads/mirror/

# update webpages
WD=$(dirname $0)
python $WD/releasepage.py /home/drew/uploads/mirror
python $WD/nightlypage.py /home/drew/uploads/cron
python $WD/mainpage.py
