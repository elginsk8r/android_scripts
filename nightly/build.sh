#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

run_build () {
    local target=$1 args="otapackage" buildstart=$(date +%s)
    local threads=$(($(cat /proc/meminfo | head -n1 | awk '{print $2}')/1000000))
    test $(($threads % 2)) -eq 1 && ((threads++))
    test "$target" = "passion" && args+=" systemupdatepackage"
    source build/envsetup.sh || return 1
    breakfast $target || return 1
    make clobber || return 1
    make -j $threads $args || return 1
    return 0
}

run_build $EV_NIGHTLY_TARGET
