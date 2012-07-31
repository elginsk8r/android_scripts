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
DISABLECCACHE=0
RELEASEBUILD=0

# dont modify
FAILNUM=0
FAILLIST=(zero)
TIMESTART=`date +%s`

function print_help() {
cat <<EOF
Usage:
  `basename $0` -acdhiklmnrsuw -p <path> -t <target>|"<target> <target>"

Options:
-a     optimize a lot (depends on -l) *depreciated*
-c     special case for cronjobs *implies -n*
-d     dont upload
-h     show this help
-i     build kernel inline
-k     clobber tree
-l     linaro build *implies -u*
-m     also build miniskirt *for passion only*
-n     build nightly
-p     directory(path) for upload (appended to ${UL_PATH}${UL_DIR}-)
-r     release build *uploads to Release/<device>*
-s     sync repo
-t     build specified target(s) *multiple targets must be in quotes*
-u     disable ccache (uncached)
-w     working directory (requires arg)
Additional Arguments:
help   show this help
fuckit no-op to get past the no args error and build with defaults.
EOF
}

# Accepts 2 args detailing the issue
function log_fail() {
    # increment first, item 0 will be used as the sentinal
    ((++FAILNUM))
    FAILLIST[$FAILNUM]="$2 failed at $1"
}

function print_failures() {
    echo "START FAILURES" | tee -a $REPORT_FILE
    while [ $FAILNUM -gt 0 ]; do
        echo "${FAILLIST[$FAILNUM]}" | tee -a $REPORT_FILE
        ((--FAILNUM))
    done
    echo "END FAILURES" | tee -a $REPORT_FILE
}

# Up to 1 arg: 1. Error message
function bail() {
    [ -z "$1" ] && exit
    echo "$1" | tee -a $REPORT_FILE
    exit
}

# Pass the starttime to it $1
function calc_run_time() {
    declare -i h_ m_ s_ d_ f_=`date +%s` b_=$1
    d_=$((f_-b_));h_=$((d_/3600))
    m_=$(($((d_-$((3600*h_))))/60));s_=$((d_-$((3600*h_))-$((60*m_))))
    echo "BUILD TIME: ${h_}h ${m_}m ${s_}s" | tee -a $REPORT_FILE
}

function get_changelog() {
    current=`date +%Y%m%d`
    pushd build
    previous=`git status -bsz`
    previous=${previous#\#\#\ }     # Too hacky?
    popd
    changelog="${previous}..${current}"
    repo sync -fd -j 12
    repo start ${current} --all
    [ -d ./changelogs ] || mkdir ./changelogs
    repo forall -pvc git log --oneline --no-merges ${previous}..${current} | tee ./changelogs/gitlog-${changelog}.log
    echo "Created changelog ${changelog}" | tee -a $REPORT_FILE
    return 0
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

while getopts ":ansdkhcimlup:t:w:r" opt; do
    case $opt in
        a) OPT3=1;;
        n) NIGHTLY=1;;
        s) SYNC=1;;
        d) UPLOAD=0;;
        p) UL_DIR=${UL_DIR}-$OPTARG;;
        k) CLOBBER=1;;
        t) TARGETLIST=($OPTARG);;
        h) print_help; bail;;
        c) CRONJOB=1;NIGHTLY=1;;
        i) KERNEL=1;;
        m) PMINI=1;;
        l) LBUILD=1;DISABLECCACHE=1;;
        u) DISABLECCACHE=1;;
        w) WORKING_DIR="$OPTARG";;
        r) RELEASEBUILD=1;;
        \?) echo "Invalid option -$OPTARG"; print_help; bail;;
        :) echo "Option -$OPTARG requires an argument."; bail;;
    esac
done

# Try and avoid mixed builds
[ $DISABLECCACHE -eq 1 ] && [ -n "$USE_CCACHE" ] && unset USE_CCACHE

[ -n "$WORKING_DIR" ] && pushd "$WORKING_DIR"
[ -e build/envsetup.sh ] || bail "You are not in the build tree"
# Set env
. build/envsetup.sh

# device array
if [ -e vendor/$SHORTVENDOR/vendorsetup.sh ] && [ -z "$TARGETLIST" ]; then
    TARGETLIST=($(<vendor/$SHORTVENDOR/vendorsetup.sh))
    # at this point every other entry is add_lunch_combo, so remove them
    TARGETLIST=(${TARGETLIST[@]/add_lunch_combo/})
    # the rest of this script relies on uniform naming, ie passion
    # ev_passion-eng will not work so remove pre/post fixes
    TARGETLIST=(${TARGETLIST[@]#*_})
    TARGETLIST=(${TARGETLIST[@]%-*})
fi

# Just in case
[ -z "$TARGETLIST" ] && bail "Unable to fetch build targets"

[ $SYNC -eq 1 ] && get_changelog

# Prepend extra path if needed
[ $CRONJOB -eq 1 ] && UL_DIR="${UL_CRON_PATH}/${UL_DIR}"
# set release upload path
[ $RELEASEBUILD -eq 1 ] && UL_DIR="Releases"
# Set full upload path now (execpt for releases which are appended later)
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

    echo  "BREAKFAST: $target" | tee -a $REPORT_FILE
    breakfast $target || { log_fail breakfast $target; continue; }

    [ $KERNEL -eq 1 ] && find_deps

    if [ $CLOBBER -eq 1 ]; then
        echo "CLOBBERING" | tee -a $REPORT_FILE
        make clobber || { log_fail clobber $target; continue; }
    else
        echo "CLEANING: $target" | tee -a $REPORT_FILE
        make clean || { log_fail clean $target; continue; }
    fi

    # google devices get fastboot tarballs
    if [ "$target" = "passion" ] || \
       [ "$target" = "grouper" ] || \
       [ "$target" = "toro" ]; then
           buildargs+=" fastboot_tarball"
    fi

    [ $NIGHTLY -eq 1 ] && buildargs+=" NIGHTLY_BUILD=true"
    [ $KERNEL -eq 1 ] && buildargs+=" BUILD_KERNEL=true"
    if [ $LBUILD -eq 1 ]; then
        buildargs+=" LINARO_BUILD=true"
        [ $OPT3 -eq 1 ] && buildargs+=" LINARO_OPT3=true"
    fi

    startime=`date +%s`

    echo "BUILDING: $target with $buildargs" | tee -a $REPORT_FILE
    schedtool -B -n 0 -e ionice -n 0 make -j 16 $buildargs || { log_fail make $target; continue; }

    calc_run_time $startime

    # upload
    # for releases append an extra path (this is just horrible)
    if [ $RELEASEBUILD -eq 1 ]; then
        case $target in
            "bravo") DEVPATH="Desire/";;
            "passion") DEVPATH="NexusOne/";;
            "inc") DEVPATH="inc/";;
            "supersonic") DEVPATH="Evo4G/";;
            "grouper") DEVPATH="Nexus7/";;
            "toro") DEVPATH="toro/";;
            "shooter") DEVPATH="Evo3D/";;
            "ruby") DEVPATH="Amaze4G/";;
            "tenderloin") DEVPATH="TouchPad/";;
            "jewel") DEVPATH="Evo4GLTE/";;
            *) DEVPATH="";;
        esac
    else
        DEVPATH="";
    fi
    [ $UPLOAD -eq 0 ] && continue
    zipname=`find out/target/product/$target \
        -name "${ZIPPREFIX}*${target}*.zip" -print0 -quit`
    # we cant upload a non existent file
    if [ -z "$zipname" ]; then
        log_fail upload_nozipfound $target; continue
    else
        echo "UPLOADING: `basename $zipname`" | tee -a $REPORT_FILE
        rsync -P -e "ssh -p2222" $zipname \
            ${GOOUSER}@${GOOHOST}:${UL_PATH}${DEVPATH} || log_fail rsync $target
    fi
    # google devices will have a tarball
    zipname=`find out/target/product/$target \
        -name "${ZIPPREFIX}*${target}*.tar.xz" -print0 -quit`
    # we cant upload a non existent file
    [ -z "$zipname" ] && continue
    echo "UPLOADING: `basename $zipname`" | tee -a $REPORT_FILE
    rsync -P -e "ssh -p2222" $zipname \
            ${GOOUSER}@${GOOHOST}:${UL_PATH}${DEVPATH} || log_fail rsync $target

done

# create log directory
[[ ! -d `dirname $REPORT_FILE` ]] && mkdir -p `dirname $REPORT_FILE`

print_failures
calc_run_time $TIMESTART

echo "Upload url: http://${GOOHOST#upload?}/devs/${GOOUSER}/${UL_DIR}/" | tee -a $REPORT_FILE
[ -n "$WORKING_DIR" ] && popd
exit
