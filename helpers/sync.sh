#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

reset_tree () {
    echo "Sync failed!"
    echo "Cleaning"
    repo forall -c git clean -fd >/dev/null 2>&1 || return 1
    echo "Resetting"
    repo forall -c git reset --hard >/dev/null 2>&1 || return 1
    echo "Resyncing"
    repo sync -fd -j12 >/dev/null || return 1
    return 0
}

sync_tree () {
    repo sync -fd -j12 >/dev/null || reset_tree
    if [ $? -ne 0 ]; then
        echo "Sync failed again?"
        echo "Dumping Status:"
        repo status
        return 1
    fi
    return 0
}

update_branch () {
    local current=$1
    repo start $current --all >/dev/null 2>&1
    echo $current > .previous_branch
    return 0
}

get_changelog () {
    local current previous
    current=$(date +%Y.%m.%d)
    if [ -f .previous_branch ]; then
        previous=$(cat .previous_branch)
    else
        echo "No previous branch!"
        sync_tree || return 1
        echo "Init $current as base for next build"
        update_branch $current
        return 0
    fi
    echo "${previous}..${current}"
    sync_tree || return 1
    update_branch $current
    repo forall -pvc git log --oneline --no-merges ${previous}..${current} 2>/dev/null
    repo sync -fdl -j12 >/dev/null 2>&1
    return 0
}

get_changelog
