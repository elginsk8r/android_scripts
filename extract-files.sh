#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

if [ $# -lt 2 ]; then
    echo "Usage $0 <vendor> <device> [serialnumber]"
    exit 1
fi
if [ ! -d build ]; then
    echo "Run this from the top of your android tree"
    exit 1
fi

VENDOR=$1
DEVICE=$2
test "$3" && SERIAL="-s $3"
BLOBFILE=device/$VENDOR/$DEVICE/proprietary-blobs.txt
OUTDIR=vendor/$VENDOR/$DEVICE/
BASE=${OUTDIR}blobs/

if [ -d $OUTDIR ]; then
    rm -r ${OUTDIR}*
else
    mkdir -p $OUTDIR
fi

for FILE in $(cat $BLOBFILE | grep -v ^# | grep -v ^$); do
    if [ ! -d ${BASE}$(dirname ${FILE#/system}) ]; then
        mkdir -p ${BASE}$(dirname ${FILE#/system})
    fi
    echo "$FILE -> ${BASE}${FILE#/system}"
    adb $SERIAL pull $FILE ${BASE}${FILE#/system}
done

(cat << EOF) > ${OUTDIR}device-vendor-blobs.mk
# Copyright (C) 2013 The Evervolv Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This file was generated from $BLOBFILE

PRODUCT_COPY_FILES += \\
EOF

LINEEND=" \\"
COUNT=$(cat $BLOBFILE | grep -v ^# | grep -v ^$ | wc -l | awk '{print $1}')
for FILE in $(cat $BLOBFILE | grep -v ^# | grep -v ^$); do
    COUNT=$(expr $COUNT - 1)
    if [ $COUNT = "0" ]; then
        LINEEND=""
    fi
    echo "    ${BASE}${FILE#/system/}:${FILE#/}:${VENDOR}$LINEEND" >> ${OUTDIR}device-vendor-blobs.mk
done

(cat << EOF) > ${OUTDIR}device-vendor.mk
# Copyright (C) 2013 The Evervolv Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

\$(call inherit-product, ${OUTDIR}device-vendor-blobs.mk)
EOF

(cat << EOF) > ${OUTDIR}BoardConfigVendor.mk
# Copyright (C) 2013 The Evervolv Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

USE_CAMERA_STUB := false
EOF
