#!/bin/bash

write_log () {
    echo "$@" >> $EV_BUILDLOG
}

upload_build () {
    local target=$1
    local remote_path=$2
    # Locate zip and optional tarball
    local local_files="$(find out/target/product/$target -name Evervolv*.zip)"
    write_log "Uploading..."
    for file in $local_files; do
        write_log "$(basename $file)"
        rsync -P -e "ssh -p${DROID_HOST_PORT}" ${file} ${DROID_USER}@${DROID_HOST}:${remote_path} >/dev/null 2>&1 || write_log "Upload failed"
    done
    return 0
}

function mirror_build () {
    local target=$1
    local mirror_path=$2
    local local_files="$(find out/target/product/$target -name Evervolv*.zip)"
    write_log "Mirroring..."
    for file in $local_files; do
        write_log "$(basename $file)"
        rsync -P ${file} ${DROID_LOCAL_MIRROR}/${mirror_path} >/dev/null 2>&1 || write_log "Mirroring failed"
    done
    return 0
}

test "$DROID_USER"      || exit 1
test "$DROID_HOST"      || exit 1
test "$DROID_HOST_PORT" || DROID_HOST_PORT=22

upload_build $EV_NIGHTLY_TARGET $EV_UPLOAD_PATH

test "$DROID_LOCAL_MIRROR" || exit 1

mirror_build $EV_NIGHTLY_TARGET ${EV_UPLOAD_PATH#*uploads/}
