#!/bin/sh

if [ $# -lt 2 ]; then
    echo "Usage $0 <vendor> <device> [serialnumber]"
    exit
fi

VENDOR=$1
DEVICE=$2
test "$3" && SERIAL="-s $3"
OUTDIR=vendor/$VENDOR/$DEVICE
DEVICEMAKEFILE=../../../$OUTDIR/device-vendor.mk
BASE=../../../$OUTDIR/proprietary

rm -rf $BASE/*

for FILE in $(cat proprietary-blobs.txt | grep -v ^# | grep -v ^$); do
    adb $SERIAL pull $FILE $BASE/$(basename $FILE)
done

chmod 755 $BASE/*.so # 755 the libs

(cat << EOF) > ../../../$OUTDIR/device-vendor-blobs.mk
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

# This file was generated from device/$VENDOR/$DEVICE/proprietary-blobs.txt

PRODUCT_COPY_FILES += \\
EOF

LINEEND=" \\"
COUNT=$(cat proprietary-blobs.txt | grep -v ^# | grep -v ^$ | wc -l | awk '{print $1}')
for FILE in $(cat proprietary-blobs.txt | grep -v ^# | grep -v ^$); do
    COUNT=$(expr $COUNT - 1)
    if [ $COUNT = "0" ]; then
        LINEEND=""
    fi
    echo "    $OUTDIR/proprietary/$(basename $FILE):$(echo $FILE | sed s#^/##)$LINEEND" >> ../../../$OUTDIR/device-vendor-blobs.mk
done

(cat << EOF) > ../../../$OUTDIR/device-vendor.mk
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

# This file was generated from device/$VENDOR/$DEVICE/proprietary-blobs.txt

\$(call inherit-product, $OUTDIR/device-vendor-blobs.mk)
EOF

(cat << EOF) > ../../../$OUTDIR/BoardConfigVendor.mk
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

# This file was generated from device/$VENDOR/$DEVICE/proprietary-blobs.txt

USE_CAMERA_STUB := false
EOF
