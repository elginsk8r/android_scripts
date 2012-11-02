#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

run_build () {
    local target=$1 args="otapackage"
    local threads=$(($(cat /proc/meminfo | head -n1 | awk '{print $2}')/1000000))
    threads=$(($threads + $(($threads % 2)))) # Round odd number up
    test "$target" = "passion" && args+=" systemupdatepackage"
    source build/envsetup.sh >/dev/null 2>&1 || return 1
    breakfast $target        >/dev/null 2>&1 || return 1
    make clobber             >/dev/null 2>&1 || return 1
    make -j $threads $args   2>&1 >/dev/null | grep -B 1 -A 6 -e error:
    return ${PIPESTATUS[0]} # Return code for make
}

run_build $EV_BUILD_TARGET
