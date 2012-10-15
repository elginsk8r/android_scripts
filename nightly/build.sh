#!/bin/bash

write_log () {
    echo "$@" >> $EV_BUILDLOG
}

fatal_error () {
    write_log $@
    exit 1
}

get_build_time () {
    declare -i h_ m_ s_ d_ f_=`date +%s` b_=$1
    d_=$((f_-b_));h_=$((d_/3600))
    m_=$(($((d_-$((3600*h_))))/60));s_=$((d_-$((3600*h_))-$((60*m_))))
    write_log "Build time: ${h_}h ${m_}m ${s_}s"
}

run_build () {
    local target=$1 args=otapackage buildstart=$(date +%s)
    local threads=$(($(cat /proc/meminfo | head -n1 | awk '{print $2}')/1000000))
    test "$target" = "passion" && args+=" systemupdatepackage"
    write_log "Building ${target}..."
    source build/envsetup.sh || fatal_error "setenv failed"
    breakfast $target >/dev/null 2>&1 || fatal_error "breakfast failed"
    make clobber >/dev/null 2>&1 || fatal_error "clobbering failed"
    make -j $threads $args >/dev/null 2>&1 || fatal_error "building failed"
    get_build_time $buildstart
}

run_build $EV_NIGHTLY_TARGET
