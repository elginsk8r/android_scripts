#!/bin/bash
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

if [ $# -ne 3 ]; then
    echo "Usage $0 <path/to/system.img> <vendor> <device>"
    exit 1
fi

if [ ! -d build ]; then
    echo "Run this from the top of your android tree"
    exit 1
fi

if [ ! -x ./out/host/linux-x86/bin/simg2img ]; then
    echo "Run 'make simg2img_host'"
    exit 1
fi

SYSTEMIMG=$1
VENDOR=$2
DEVICE=$3
TEMPDIR=$(mktemp -d)
TEMPIMG=$(mktemp)
PRODUCT=$VENDOR/$DEVICE
BLOBFILE=device/$PRODUCT/proprietary-blobs.txt
OUTDIR=vendor/$PRODUCT
BASE=$OUTDIR/proprietary

if [ ! -d $BASE ]; then
    mkdir -p $BASE
else
    rm -rf $BASE/*
fi

./out/host/linux-x86/bin/simg2img $SYSTEMIMG $TEMPIMG
sudo mount -t ext4 -o loop $TEMPIMG $TEMPDIR

for FILE in $(cat $BLOBFILE | grep -v ^# | grep -v ^$); do
    cp -v ${TEMPDIR}${FILE#/system} $BASE/$(basename $FILE)
done

sudo umount $TEMPDIR
rm -r $TEMPDIR
rm -r $TEMPIMG

(cat << EOF) > $OUTDIR/device-vendor-blobs.mk
# Copyright (C) 2012 The Android Open Source Project
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
    echo "    $BASE/$(basename $FILE):$(echo $FILE | sed s#^/##)$LINEEND" >> $OUTDIR/device-vendor-blobs.mk
done

(cat << EOF) > $OUTDIR/device-vendor.mk
# Copyright (C) 2012 The Android Open Source Project
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

\$(call inherit-product, $OUTDIR/device-vendor-blobs.mk)
EOF

(cat << EOF) > $OUTDIR/BoardConfigVendor.mk
# Copyright (C) 2012 The Android Open Source Project
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

USE_CAMERA_STUB := false
EOF
