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
REPORT_FILE=~/db-logs/report-`date +%Y%m%d`

# for getopts
SYNC=0
UPLOAD=1
CLOBBER=0
NIGHTLY=0
CRONJOB=0
KERNEL=0
PMINI=0
LBUILD=0
OPT3=0

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
    TARGETLIST=
fi

function print_help() {
cat <<EOF
Usage: `basename $0` -acdhiklmns -p <path> -t <target>|"<target> <target>"

Options:
-a     optimize a lot (depends on -l)
-c     special case for cronjobs
-d     dont upload
-h     show this help
-i     build kernel inline
-k     clobber tree
-l     linaro build
-m     also build miniskirt (for passion only)
-n     build nightly
-p     directory(path) for upload (appended to ${UL_PATH}${UL_DIR}-)
-s     sync repo
-t     build specified target(s)
Additional Arguments:
help   show this help
douche no-op to get past the no args error and build with defaults
         this is not recommended.. you should at least run -s
EOF
}

# Accepts 2 args detailing the issue
function log_fail() {
    # increment first, item 0 will be used as the sentinal
    ((++FAILNUM))
    FAILLIST[$FAILNUM]="$2 failed at $1"
    echo ${FAILLIST[$FAILNUM]}
}

function print_failures() {
    while [ $FAILNUM -gt 0 ]; do
        echo "${FAILLIST[$FAILNUM]}" | tee -a $REPORT_FILE
        ((--FAILNUM))
    done
}

# Up to 1 arg: 1. Error message
function bail() {
    [ -z "$1" ] && exit
    echo "$1"
    exit
}

# Requires TIMESTART=`date +%s` at beginning of file
function calc_run_time() {
    declare -i h_ m_ s_ f_ d_
    f_=`date +%s`;d_=$((f_-TIMESTART));h_=$((d_/3600))
    m_=$(($((d_-$((3600*h_))))/60));s_=$((d_-$((3600*h_))-$((60*m_))))
    echo "BUILD TIME: ${h_}h ${m_}m ${s_}s" | tee -a $REPORT_FILE
}

#
# Start main
#
if [ $# -eq 0 ]; then
    echo "This script cannot be called without arguments"; print_help; bail;
fi

if [ "$1" == "help" ]; then
    print_help; bail;
fi

while getopts ":ansdkhcimlp:t:" opt; do
    case $opt in
        a) OPT3=1;;
        n) NIGHTLY=1;;
        s) SYNC=1;;
        d) UPLOAD=0;;
        p) UL_DIR=${UL_DIR}-$OPTARG;;
        k) CLOBBER=1;;
        t) TARGETLIST=($OPTARG);;
        h) print_help; bail;;
        c) CRONJOB=1;;
        i) KERNEL=1;;
        m) PMINI=1;;
        l) LBUILD=1;;
        \?) echo "Invalid option -$OPTARG"; print_help; bail;;
        :) echo "Option -$OPTARG requires an argument."; bail;;
    esac
done

# Try and avoid mixed builds
[ $LBUILD -eq 1 ] && [ -n "$USE_CCACHE" ] && unset USE_CCACHE

[ -e build/envsetup.sh ] || bail "You are not in the build tree"
# Set env
. build/envsetup.sh

if [ $SYNC -eq 1 ]; then
    repo sync -j16 || log_fail sync repo
fi

if [ $CLOBBER -eq 1 ]; then
    make clobber || log_fail clobber make
fi

# Prepend extra path if needed
[ $CRONJOB -eq 1 ] && UL_DIR="${UL_CRON_PATH}/${UL_DIR}"

# Set full upload path now
UL_PATH+="${UL_DIR}/"

# Append the miniskirt target for use later
[ $PMINI -eq 1 ] && TARGETLIST=(${TARGETLIST[@]} miniskirt)

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

    echo  "BREAKFAST: $target"
    breakfast $target || { log_fail breakfast $target; continue; }

    [ $KERNEL -eq 1 ] && find_deps

    echo "CLEANING: $target"
    make clean || { log_fail clean $target; continue; }

    # passion also gets fastboot images
    [ "$target" == "passion" ] && buildargs+=" fastboot_tarball"

    [ $NIGHTLY -eq 1 ] && buildargs+=" NIGHTLY_BUILD=true"
    [ $KERNEL -eq 1 ] && buildargs+=" BUILD_KERNEL=true"
    if [ $LBUILD -eq 1 ]; then
        buildargs+=" LINARO_BUILD=true"
        [ $OPT3 -eq 1 ] && buildargs+=" LINARO_OPT3=true"
    fi

    echo "BUILDING: $target with $buildargs"
    schedtool -B -n 5 -e ionice -n 5 make -j 10 $buildargs || { log_fail mka $target; continue; }

    # upload
    [ $UPLOAD -eq 0 ] && continue
    zipname=`find out/target/product/$target \
        -name "${ZIPPREFIX}*${target}*.zip" -print0 -quit`
    # we cant upload a non existent file
    if [ -z "$zipname" ]; then
        log_fail upload_nozipfound $target; continue
    else
        echo "UPLOADING: `basename $zipname`"
        rsync -P -e "ssh -p2222" $zipname \
            ${GOOUSER}@${GOOHOST}:${UL_PATH} || log_fail rsync $target
    fi
    # upload the extra passion file
    [ "$target" == "passion" ] || continue
    zipname=`find out/target/product/$target \
        -name "${ZIPPREFIX}*${target}*.tar.bz2" -print0 -quit`
    # we cant upload a non existent file
    if [ -z "$zipname" ]; then
        log_fail upload_notarballfound $target; continue
    else
        echo "UPLOADING: `basename $zipname`"
        rsync -P -e "ssh -p2222" $zipname \
            ${GOOUSER}@${GOOHOST}:${UL_PATH} || log_fail rsync $target
    fi
done

# create log directory
[[ ! -d `dirname $REPORT_FILE` ]] && mkdir -p `dirname $REPORT_FILE`

print_failures
calc_run_time

echo "Upload url: http://${GOOHOST#upload?}/devs/${GOOUSER}/${UL_DIR}/" | tee -a $REPORT_FILE

exit
