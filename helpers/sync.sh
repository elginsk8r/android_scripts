#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

reset_tree () {
    echo "Sync failed..."
    echo "Cleaning"
    repo forall -c git clean -fd >/dev/null 2>&1 || return 1
    echo "Resetting"
    repo forall -c git reset --hard >/dev/null 2>&1 || return 1
    echo "Resyncing"
    repo sync -fd -j12 >/dev/null || return 1
    return 0
}

get_changelog () {
    local current previous
    current=$(date +%Y.%m.%d)
    if [ -f .previous_branch ]; then
        previous=$(cat .previous_branch)
    else
        pushd build >/dev/null 2>&1
        previous=$(git status -bsz)
        previous=${previous#\#\#\ } # Too hacky?
        popd >/dev/null 2>&1
        if [ "$previous" = "HEAD (no branch)" ]; then
            echo "No previous branch found"
            return 1
        fi
    fi
    echo "${previous}..${current}"
    repo sync -fd -j12 >/dev/null || reset_tree
    if [ $? -ne 0 ]; then
        echo "Sync failed again"
        echo "Dumping Status:"
        repo status
        return 1
    fi
    repo start ${current} --all >/dev/null 2>&1
    echo $current > .previous_branch
    repo forall -pvc git log --oneline --no-merges ${previous}..${current} 2>/dev/null
    return 0
}

get_changelog
