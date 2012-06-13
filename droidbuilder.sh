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
UL_PATH="~/public_html/"

# location to upload when building from a cron job
# format $UL_PATH/$UL_CRON_PATH/$UL_DIR
# CAREFUL this directory must be pre-existing rsync wont make parents
UL_CRON_PATH="cron"

# Assumes zip naming ${ZIPPREFIX}*${target}*.zip
# $ZIPPREFIX followed by anything, then $target followed by anything, then .zip
# where $target is element of $TARGETLIST
ZIPPREFIX="Evervolv"

# vendor path (ie /vendor/ev)
SHORTVENDOR="ev"

# report file
REPORT_FILE=report-`date +%Y%m%d`

# for getopts
SYNC=0
UPLOAD=1
CLOBBER=0
NIGHTLY=0
CRONJOB=0
KERNEL=0
PMINI=0
LBUILD=0

# dont modify
FAILNUM=0
FAILLIST=(zero)
TIMESTART=`date +%s`


# device array
if [ -e vendor/$SHORTVENDOR/vendorsetup.sh ]; then
    TARGETLIST=($(<vendor/$SHORTVENDOR/vendorsetup.sh))
    # at this point every other entry is add_lunch_combo, so remove them
    TARGETLIST=(${TARGETLIST[@]/add_lunch_combo/})
    # the rest of this script relies on uniform naming, ie passion
    # ev_passion-eng will not work so remove pre/post fixes
    TARGETLIST=(${TARGETLIST[@]#*_})
    TARGETLIST=(${TARGETLIST[@]%-*})
else
    TARGETLIST=(bravo epic4gtouch inc passion ruby shooter supersonic)
fi

function __help() {
cat <<EOF
Usage: `basename $0` -acdhiklmns -p <path> -t <target>|"<target> <target>"

Options:
-a     build all targets
-c     special case for cronjobs
-d     dont upload
-h     show this help
-i     build kernel inline
-k     clobber tree
-l     linaro build
-m     also build miniskirt (for passion only)
-n     build nightly
-p     directory(path) for upload (appended to $UL_PATH)
-s     sync repo
-t     build specified target(s)
EOF
}

# accepts 2 args detailing the issue
function __fail() {
    # increment first, item 0 will be used as the sentinal
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
    echo " *** Time calculation: $usedhours h, $usedminutes m, $usedseconds s *** " | tee -a ~/droidbuilder/${REPORT_FILE}
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

while getopts ":ansdkhcimlp:t:" opt; do
    case $opt in
        a) ;; # noop
        n) NIGHTLY=1;;
        s) SYNC=1;;
        d) UPLOAD=0;;
        p) UL_DIR=$OPTARG;;
        k) CLOBBER=1;;
        t) TARGETLIST=($OPTARG);;
        h) __help; exit;;
        c) CRONJOB=1;;
        i) KERNEL=1;;
        m) PMINI=1;;
        l) LBUILD=1;;
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

# Append extra path if needed
if [ $CRONJOB -eq 1 ]; then
    UL_PATH+="${UL_CRON_PATH}/"
fi

# Set full upload path now
UL_PATH+="${UL_DIR}/"

# Append the miniskirt target for use later
if [ $PMINI -eq 1 ]; then
    TARGETLIST=(${TARGETLIST[@]} miniskirt)
fi

# Try and avoid mixed builds
[ $LBUILD -eq 1 ] && export USE_CCACHE=0

# loop the TARGETLIST array and build all targets present
# if a step errors the step is logged to FAILLIST and the loop
# continues to the next item in TARGETLIST
for (( ii=0 ; ii < ${#TARGETLIST[@]} ; ii++ )) ; do

    target=${TARGETLIST[$ii]}

    buildargs="otapackage"

    # the miniskirt target is not valid it is merely used to
    # append the MINISKIRT build arg and needs to be redefined
    # properly as passion
    if [ "$target" == "miniskirt" ]; then
        target="passion"
        buildargs+=" MINISKIRT=true"
    fi

    echo  "BREAKFAST for: $target"
    breakfast $target || { __fail breakfast $target; continue; }

    if [ $KERNEL -eq 1 ]; then
        find_deps
    fi

    echo "CLEAN for: $target"
    make clean || { __fail clean $target; continue; }

    # passion also gets fastboot images
    if [ "$target" == "passion" ]; then
        buildargs+=" fastboot_tarball"
    fi

    if [ $NIGHTLY -eq 1 ]; then
        buildargs+=" NIGHTLY_BUILD=true"
    fi

    if [ $KERNEL -eq 1 ]; then
        buildargs+=" BUILD_KERNEL=true"
    fi

    if [ $LBUILD -eq 1 ]; then
        buildargs+=" LINARO_BUILD=1"
    fi

    echo "BUILD for: $target: args = $buildargs"
    schedtool -B -n 1 -e ionice -n 1 make -j 8 $buildargs || { __fail mka $target; continue; }

    # upload
    if [ $UPLOAD -eq 1 ]; then

        zipname=`find out/target/product/$target -name "${ZIPPREFIX}*${target}*.zip" -print0 -quit`
        # we cant upload a non existent file
        if [ -z "$zipname" ]; then
            __fail upload_nozipfound $target; continue
        else
            echo "UPLOADING $zipname"
            rsync -P -e "ssh -p2222" $zipname ${GOOUSER}@${GOOHOST}:${UL_PATH} || __fail rsync $target
        fi
        # upload the extra passion file
        if [ "$target" == "passion" ]; then
            zipname=`find out/target/product/$target -name "${ZIPPREFIX}*${target}*.tar.bz2" -print0 -quit`
            # we cant upload a non existent file
            if [ -z "$zipname" ]; then
                __fail upload_notarballfound $target; continue
            else
                echo "UPLOADING `basename $zipname`"
                rsync -P -e "ssh -p2222" $zipname ${GOOUSER}@${GOOHOST}:${UL_PATH} || __fail rsync $target
            fi
        fi
    fi
    # end upload
done

# create log directory
if [ ! -d ~/droidbuilder ]; then
    mkdir -p ~/droidbuilder
fi

# Print all failures at the end so we actually see them!
while [ $FAILNUM -gt 0 ]; do
    echo ${FAILLIST[$FAILNUM]} | tee -a ~/droidbuilder/${REPORT_FILE}
    ((--FAILNUM))
done

__calc_run_time

echo "Files were uploaded to: http://${GOOHOST#upload?}/devs/$GOOUSER/$UL_DIR/" | tee -a ~/droidbuilder/${REPORT_FILE}

exit
