#!/bin/bash

write_log () {
    echo "$@" >> $EV_BUILDLOG
}

upload () {
    local local_file=$1
    local remote_path=$2
    write_log "Uploading $(basename $local_file)"
    rsync -P -e "ssh -p${DROID_HOST_PORT}" ${local_file} ${DROID_USER}@${DROID_HOST}:${remote_path} >/dev/null 2>&1 || write_log "Upload failed"
    return 0
}

mirror () {
    local local_file=$1
    local mirror_path=$2
    write_log "Mirroring $(basename $local_file)"
    rsync -P ${local_file} ${DROID_LOCAL_MIRROR}/${mirror_path} >/dev/null 2>&1 || write_log "Mirroring failed"
    return 0
}

# Fetch from environment
test "$DROID_USER" || exit 1
test "$DROID_HOST" || exit 1
test "$DROID_HOST_PORT" || DROID_HOST_PORT=22

upload $EV_HTML_CHANGELOG $EV_UPLOAD_PATH
upload $EV_HTML_BUILDLOG $EV_UPLOAD_PATH

test "$DROID_LOCAL_MIRROR" || exit 1

mirror $EV_CHANGELOG ${EV_UPLOAD_PATH#*uploads/}
mirror $EV_BUILDLOG ${EV_UPLOAD_PATH#*uploads/}
