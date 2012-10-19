#!/bin/bash
#
# Build android for all targets present in TARGETLIST and upload
# Author: Andrew Sutherland <dr3wsuth3rland@gmail.com>
#

# variables pulled from Environment
#
# for ssh (assumes public ssh key in use)
# DROID_USER
# DROID_HOST
# DROID_HOST_PORT (defaults to 22 if not specified)
#
# to keep local copies of releases something like
# /media/NFS/releases/<codename> (codename is appended)
# DROID_LOCAL_MIRROR
#

# GLOBALS
#
# date Y.M.D
DATE=$(date +%Y.%m.%d)
# date stamped folder (override with -p)
UL_DIR=$DATE
# upload path
UL_PATH="~/uploads/"
# Assumes zip naming ${ZIPPREFIX}*${target}*.zip
# $ZIPPREFIX followed by anything, then $target followed by anything, then .zip
# where $target is element of $TARGETLIST
ZIPPREFIX="Evervolv"
# vendor path (ie /vendor/ev)
SHORTVENDOR="ev"
# report file
REPORT_FILE=~/db-logs/buildlog-${DATE}.log
# create log directory
[ -d `dirname $REPORT_FILE` ] || mkdir -p `dirname $REPORT_FILE`

# for getopts
SYNC=0
UPLOAD=1
CLOBBER=0
NIGHTLY=0
KERNEL=0
PMINI=0
LBUILD=0
DISABLECCACHE=0
RELEASEBUILD=0
KERNJOBS=0
QUIET=0
MIRRORUPLOAD=0

# dont modify
FAILNUM=0
FAILLIST=(zero)
TIMESTART=`date +%s`

function print_help() {
cat <<EOF
Usage:
  `basename $0` -dhilmnqrsu -t <target>|"<target> <target>"
                  -j <jobs> -p|a <path> -w <workingdir>
Options:
-a     append upload path ${UL_PATH}${UL_DIR}-<OPTARG>
-d     dont upload
-h     show this help
-i     build kernel inline
-j     specify the number of jobs to use for KERNEL_JOBS (depends on -i)
-l     linaro build (implies -u and -i)
-m     also build miniskirt (for passion only)
-n     build nightly
-p     set upload path ${UL_PATH}/<OPTARG>
-q     route build output to /dev/null
-r     release build (uploads to <codename>) (implies -z)
-s     sync repo (also generates changelog)
-t     build specified target(s) (multiple targets must be in quotes)
-u     disable ccache (uncached)
-w     working directory (requires arg)
-z     mirror upload locally
Additional Arguments:
help   show this help
EOF
}

# Accepts 2 args detailing the issue
function log_fail() {
    # increment first, item 0 will be used as the sentinal
    ((++FAILNUM))
    FAILLIST[$FAILNUM]="$2 failed at $1"
}

function logit() {
    echo "$1" | tee -a $REPORT_FILE
}

function print_failures() {
    logit "START FAILURES"
    while [ $FAILNUM -gt 0 ]; do
        logit "${FAILLIST[$FAILNUM]}"
        ((--FAILNUM))
    done
    logit "END FAILURES"
}

# Up to 1 arg: 1. Error message
function bail() {
    [ -z "$1" ] && exit
    logit "$1"
    exit
}

# args: starting time, message
function calc_run_time() {
    declare -i h_ m_ s_ d_ f_=`date +%s` b_=$1
    local message="$2"
    test "$message" || message="Run time"
    d_=$((f_-b_));h_=$((d_/3600))
    m_=$(($((d_-$((3600*h_))))/60));s_=$((d_-$((3600*h_))-$((60*m_))))
    logit "$message ${h_}h ${m_}m ${s_}s"
}

# no args
function get_changelog() {
    local current previous changelog changelogfile
    current=$DATE
    pushd build
    previous=`git status -bsz`
    previous=${previous#\#\#\ }     # Too hacky?
    popd
    test "$previous" = "(no branch)" && return 1
    changelog="${previous}..${current}"
    test -d changelogs || mkdir changelogs
    changelogfile=changelogs/gitlog-${changelog}.log
    echo -n > $changelogfile # zero out
    repo sync -fd -j 12 || echo "Sync failed" > $changelogfile
    repo start ${current} --all
    repo forall -pvc git log --oneline --no-merges ${previous}..${current} >> $changelogfile
    logit "Created changelog ${changelog}"
}

# 2 args: local path to file, remote path
function push_upload () {
    local local_file=$1
    local remote_path=$2
    logit "Uploading $(basename $local_file)"
    # create directory (i cant make rsync do parents so this is a workaround)
    ssh -p${DROID_HOST_PORT} ${DROID_USER}@${DROID_HOST} \[ -d ${remote_path} \] \|\| mkdir -p ${remote_path}
    rsync -P -e "ssh -p${DROID_HOST_PORT}" ${local_file} ${DROID_USER}@${DROID_HOST}:${remote_path} || log_fail uploading $target
}

# one arg: board name: sets global DEVCODENAME
function get_device_codename () {
    local board devicedir codename
    board=$1
    devicedir=`find device/ -type d -name $board`
    codename=`cat ${devicedir}/${SHORTVENDOR}.mk | grep PRODUCT_CODENAME | sed -e s/\ //g -e s/PRODUCT_CODENAME\:=//`
    DEVCODENAME="${codename}/"
}

# 2 args: local path to file, device codename
function mirror_upload () {
    local local_file=$1
    local dev_codename=$2
    if [ $RELEASEBUILD -eq 1 ]; then
        local mirror_path="${DROID_LOCAL_MIRROR}/${dev_codename}"
    else
        local mirror_path="${DROID_LOCAL_MIRROR}/${UL_DIR}"
    fi
    [ -z "$DROID_LOCAL_MIRROR" ] && logit "DROID_LOCAL_MIRROR not set" && return
    [ -d $mirror_path ] || mkdir -p $mirror_path
    logit "Mirroring $(basename $local_file)"
    rsync -P ${local_file} ${mirror_path} || log_fail mirroring $target
}

# req $1: pid, opt $2: message
function spinner() {
    local pid=$1
    local delay=0.5
    local spinstr='|/-\'
    declare -i b_=`date +%s`
    printf "$2\t"
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        declare -i h_ m_ s_ d_ f_=`date +%s`
        d_=$((f_-b_));h_=$((d_/3600))
        m_=$(($((d_-$((3600*h_))))/60));s_=$((d_-$((3600*h_))-$((60*m_))))
        printf "%02d:%02d [%c]  " $m_ $s_ "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b\n"
}

#
# Start main
#

if [ $# -eq 0 ]; then
    echo "This script cannot be called without arguments"; print_help; bail;
fi

if [ "$1" = "help" ]; then
    print_help; bail;
fi

while getopts ":nsdhimlup:t:w:j:rqza:" opt; do
    case $opt in
        p) UL_DIR=$OPTARG
        n) NIGHTLY=1;;
        s) SYNC=1;;
        d) UPLOAD=0;;
        a) UL_DIR=${UL_DIR}-$OPTARG;;
        t) TARGETLIST=($OPTARG);;
        h) print_help; bail;;
        i) KERNEL=1;;
        j) KERNJOBS=$OPTARG;;
        m) PMINI=1;;
        l) LBUILD=1;DISABLECCACHE=1;KERNEL=1;;
        u) DISABLECCACHE=1;;
        w) WORKING_DIR="$OPTARG";;
        r) RELEASEBUILD=1;MIRRORUPLOAD=1;;
        q) QUIET=1;;
        z) MIRRORUPLOAD=1;;
        \?) echo "Invalid option -$OPTARG"; print_help; bail;;
        :) echo "Option -$OPTARG requires an argument."; bail;;
    esac
done

if [ $UPLOAD -eq 1 ]; then
    [ -z "$DROID_USER" ] && bail "DROID_USER not set for upload server"
    [ -z "$DROID_HOST" ] && bail "DROID_HOST not set for upload server"
    [ -z "$DROID_HOST_PORT" ] && DROID_HOST_PORT=22
fi

# Try and avoid mixed builds
[ $DISABLECCACHE -eq 1 ] && [ -n "$USE_CCACHE" ] && unset USE_CCACHE

[ -n "$WORKING_DIR" ] && pushd "$WORKING_DIR"
[ -e build/envsetup.sh ] || bail "You are not in the build tree"
# Set env
. build/envsetup.sh >/dev/null 2>&1

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

# Set full upload path now (execpt for releases which are appended later)
[ $RELEASEBUILD -eq 0 ] && UL_PATH+="${UL_DIR}/"

# Append the miniskirt target for use later
[ $PMINI -eq 1 ] && TARGETLIST=(${TARGETLIST[@]} miniskirt)

test $SYNC -eq 1 && get_changelog

# loop the TARGETLIST array and build all targets present
# if a step errors the step is logged to FAILLIST and the loop
# continues to the next item in TARGETLIST
for (( ii=0 ; ii < ${#TARGETLIST[@]} ; ii++ )) ; do

    target=${TARGETLIST[$ii]}

    buildargs="otapackage"

    # the miniskirt target is not valid it is merely used to
    # append the MINISKIRT build arg and needs to be redefined
    # properly as passion
    if [ "$target" = "miniskirt" ]; then
        target="passion"
        buildargs+=" MINISKIRT=true"
    fi

    logit "++Start building $target"
    breakfast $target >/dev/null 2>&1 || { log_fail breakfast $target; continue; }

    [ $KERNEL -eq 1 ] && find_deps

    logit "Cleaning"
    make clobber >/dev/null 2>&1 || { log_fail clobber $target; continue; }

    # passion gets the extra package
    test "$target" = "passion" && buildargs+=" systemupdatepackage"

    [ $NIGHTLY -eq 1 ] && buildargs+=" NIGHTLY_BUILD=true"

    if [ $KERNEL -eq 1 ]; then
        buildargs+=" BUILD_KERNEL=true"
        [ $KERNJOBS -gt 0 ] && buildargs+=" KERNEL_JOBS=$KERNJOBS"
    fi

    if [ $LBUILD -eq 1 ]; then
        buildargs+=" LINARO_BUILD=true"
    fi

    startime=`date +%s`

    logit "Make with: $buildargs"
    if [ $QUIET -eq 1 ]; then
        ( schedtool -B -n 0 -e ionice -n 0 make -j 16 $buildargs >/dev/null 2>&1 ) &
        spinner $! "Working..."
    else
        schedtool -B -n 0 -e ionice -n 0 make -j 16 $buildargs || { log_fail make $target; continue; }
    fi

    calc_run_time $startime "--End building"

    # upload
    # for releases append an extra path
    if [ $RELEASEBUILD -eq 1 ]; then
        get_device_codename $target
    else
        DEVCODENAME=""
    fi
    [ $UPLOAD -eq 0 ] && continue
    zips="$(find out/target/product/$target -name ${ZIPPREFIX}*.zip)"
    for zipfile in $zips; do
        push_upload "$zipfile" "${UL_PATH}${DEVCODENAME}"
        test $MIRRORUPLOAD -eq 1 && mirror_upload "$zipfile" "$DEVCODENAME"
    done

done

# cleanup
if [ $UPLOAD -eq 1 ]; then
    make clobber >/dev/null 2>&1 || log_fail clobber $target
fi

# print failures if there are any to report
[ $FAILNUM -gt 0 ] && print_failures

calc_run_time $TIMESTART

# copy build log
test $MIRRORUPLOAD -eq 1 && mirror_upload $REPORT_FILE

[ -n "$WORKING_DIR" ] && popd
exit
