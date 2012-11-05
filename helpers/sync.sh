#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

get_changelog () {
    local current previous changelog changelogfile=$1
    current=$(date +%Y.%m.%d)
    pushd build >/dev/null 2>&1
    previous=$(git status -bsz)
    previous=${previous#\#\#\ } # Too hacky?
    popd >/dev/null 2>&1
    test "$previous" = "(no branch)" && return 1
    changelog="${previous}..${current}"
    echo $changelog > $changelogfile
    repo sync -fd -j12 >/dev/null 2>&1 || { echo "Sync failed" >> $changelogfile; return 1 }
    repo start ${current} --all >/dev/null 2>&1
    repo forall -pvc git log --oneline --no-merges ${previous}..${current} >> $changelogfile 2>/dev/null
    return 0
}

get_changelog $EV_CHANGELOG
