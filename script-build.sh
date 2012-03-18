#!/bin/bash
#
# Build android for all targets present in TARGETLIST and upload to goo
# Author: Andrew Sutherland <dr3wsuth3rland@gmail.com>
#

# assumes public ssh key in use
GOOUSER="evervolv"
GOOHOST="upload.goo-inside.me"

# date stamped folder (override with -p)
UL_DIR=`date +%Y%m%d`
# upload path (must be preexisting)
UL_PATH="~/$GOOUSER/public_html/"
# upload command
UL_CMD="rsync -P -e \"ssh -p2222\""

# Assumes zip naming ${ZIPPREFIX}*${target}*.zip
# $ZIPPREFIX followed by anything, then $target followed by anything, then .zip
# where $target is element of $TARGETLIST
ZIPPREFIX="Evervolv"

# for getopts
SYNC=0
UPLOAD=1 #True by default
CLOBBER=0
NIGHTLY=0

# dont modify
FAILNUM=0
FAILLIST=(zero)
TIMESTART=`date +%s`


## device array
#if [ -e vendor/ev/vendorsetup.sh ]; then
#    TARGETLIST=($(<vendor/ev/vendorsetup.sh))
#    # the rest of this script relies on uniform naming
#    # ie passion, ev_passion-eng will not work so remove pre/post fixes
#    TARGETLIST=(${TARGETLIST[@]#ev_})
#    TARGETLIST=(${TARGETLIST[@]%-eng})
#    # at this point every other entry is add_lunch_combo, so remove them
#    TARGETLIST=(${TARGETLIST[@]/add_lunch_combo/})
#else
    TARGETLIST=(bravo epic4gtouch inc passion ruby shooter supersonic)
#fi

function __help() {
    echo "Usage: `basename $0` -andksh -p <path> -t <target>|\"<target> <target>\""
    echo "Options:"
    echo "-a     build all targets"
    echo "-t     build specified target(s)"
    echo "-s     sync repo"
    echo "-d     dont upload"
    echo "-p     directory(path) for upload (appended to $UL_PATH)"
    echo "-k     clobber tree"
    echo "-n     build nightly"
    echo "-h     show this help"
}

# accepts 2 args detailing the issue
function __fail() {
    #increment first, item 0 will be used as the sentinal
    ((++FAILNUM))
    FAILLIST[$FAILNUM]="$2 : failed at $1"
    echo ${FAILLIST[$FAILNUM]}
}

function __calc_run_time() {
datefinish=`date +%s`
timediff=$((datefinish - TIMESTART))
usedhours=$(( timediff / 3600 ))
usedminutes=$(( ( timediff - ( 3600 * usedhours ) ) / 60))
usedseconds=$(( timediff - ( 3600 * usedhours ) -  ( 60 * usedminutes ) ))
echo " *** Time calculation: $usedhours h, $usedminutes m, $usedseconds s *** "
}

#
# Start main
#
if [ $# -eq 0 ]; then
    echo "This script cannot be called without arguments"; __help; exit 1;
fi

if [ "$1" == "help" ]; then
    __help; exit;
fi

while getopts ":ansdkhp:t:" opt; do
    case $opt in
        a) ;; # noop
        n) NIGHTLY=1;;
        s) SYNC=1;;
        d) UPLOAD=0;;
        p) UL_DIR=$OPTARG;;
        k) CLOBBER=1;;
        t) TARGETLIST=($OPTARG);;
        h) __help; exit;;
        \?) echo "Invalid option -$OPTARG"; __help; exit 1;;
        :) echo "Option -$OPTARG requires an argument."; exit 1;;
    esac
done

if [ -e build/envsetup.sh ]; then
    . build/envsetup.sh
else
    echo "You are not in the build tree"; exit 1;
fi

if [ $SYNC -eq 1 ]; then
    repo sync -j16 || __fail sync repo
fi

if [ $CLOBBER -eq 1 ]; then
    make clobber || __fail clobber make
fi

# loop the TARGETLIST array and build all targets present
# if a step errors the step is logged to FAILLIST and the loop
# continues to the next item in TARGETLIST
for (( ii=0 ; ii < ${#TARGETLIST[@]} ; ii++ )) ; do

    target=${TARGETLIST[$ii]}

    echo  "BREAKFAST for: $target"
    breakfast $target || { __fail breakfast $target; continue; }

    echo "CLEAN for: $target"
    make clean || { __fail clean $target; continue; }

    buildargs="otapackage"

    # passion also gets fastboot images
    if [ "$target" == "passion" ]; then
        buildargs+=" fastboot_tarball"
    fi

    if [ $NIGHTLY -eq 1 ]; then
        buildargs+=" NIGHTLY_BUILD=true"
    fi

    echo "BUILD for: $target: args = $buildargs"
    mka $buildargs || { __fail mka $target; continue; }

    # upload
    if [ $UPLOAD -eq 1 ]; then
        zipname=`find out/target/product/$target -name "${ZIPPREFIX}*${target}*.zip" -print0 -quit`
        # we cant upload a non existent file
        if [ -z "$zipname" ]; then
            __fail upload_nozipfound $target
        else
            echo "UPLOADING $zipname"
            $UL_CMD $zipname ${GOOUSER}@${GOOHOST}:${UL_PATH}${UL_DIR}/ || __fail rsync $target
        fi
        # upload the extra passion file
        if [ "$target" == "passion" ]; then
            zipname=`find out/target/product/$target -name "${ZIPPREFIX}*${target}*.tar.bz2" -print0 -quit`
            # we cant upload a non existent file
            if [ -z "$zipname" ]; then
                __fail upload_notarballfound $target; continue
            else
                echo "UPLOADING `basename $zipname`"
                $UL_CMD $zipname ${GOOUSER}@${GOOHOST}:${UL_PATH}${UL_DIR}/ || __fail rsync $target
            fi
        fi
    fi
    # end upload
done

# Print all failures at the end so we actually see them!
while [ $FAILNUM -gt 0 ]; do
    echo ${FAILLIST[$FAILNUM]}
    ((--FAILNUM))
done

__calc_run_time
echo "Files were uploaded to: http://${GOOHOST#upload?}/devs/$GOOUSER/$UL_DIR/"

exit
