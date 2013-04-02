#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

run_build () {
    local target=$1 args="otapackage"
    local cpus=$(cat /proc/cpuinfo | grep "^processor" | wc -l)
    local load=$(expr $cpus \* 3 / 2)
    test "$target" = "passion" && args+=" systemupdatepackage"
    source build/envsetup.sh >/dev/null 2>&1 || return 1
    breakfast $target        >/dev/null 2>&1 || return 1
    make clobber             >/dev/null 2>&1 || return 1
    make -j -l$load $args    >/dev/null      || return 1
    return 0
}

run_build $EV_BUILD_TARGET
