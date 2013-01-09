#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

run_build () {
    local target=$1 args="otapackage"
    local threads=$(($(cat /proc/meminfo | head -n1 | awk '{print $2}')/1000000))
    threads=$(($threads + $(($threads % 2)))) # Round odd number up
    test $threads -gt 32 && threads=32 # 32 jobs is upper limit
    test "$target" = "passion" && args+=" systemupdatepackage"
    source build/envsetup.sh >/dev/null 2>&1 || return 1
    breakfast $target        >/dev/null 2>&1 || return 1
    make clobber             >/dev/null 2>&1 || return 1
    make -j$threads $args    >/dev/null      || return 1
    return 0
}

run_build $EV_BUILD_TARGET
