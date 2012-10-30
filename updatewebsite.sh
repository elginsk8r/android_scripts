#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

# Run from website root directory

base_dir=/home/drew/uploads
release_dir=mirror
nightly_dir=cron

# update release mirror
rsync -qrpt --partial -e 'ssh -p30000' evervolv@217.150.244.124:~/uploads/ $base_dir/$release_dir/

WD=$(dirname $0)

# update webpages
python $WD/releasepage.py $base_dir/$release_dir
python $WD/nightlypage.py $base_dir/$nightly_dir
python $WD/mainpage.py

# copy resources
rsync -qrpt --partial $WD/website_resources/ .
