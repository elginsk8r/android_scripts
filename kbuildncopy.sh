#!/bin/bash

# build and copy kernels

if [ $# -eq 0 ]; then
	echo "ERROR: must specify board(s) (`basename $0`-h)"; exit 1;
fi

if [ -z $CROSS_COMPILE ]; then
	echo "ERROR: you need to set your environment"; exit 1;
fi

passion=0
bravo=0
ss=0
inc=0

get_help()
{
cat <<EOF
Usage:
	p : passion
	b : bravo
	s : supersonic
	i : inc
	t : use tiamat config
	c : set config
	d : set destination directory
	h : show this
EOF
}

while getopts "pbsithc:d:" opt; do
	case $opt in
		p) passion=1;;
		b) bravo=1;;
		s) ss=1;;
		i) inc=1;;
		t) config="tiamat";;
		h) get_help;;
		c) config=$OPTARG;;
		d) sourcedir=$OPTARG;;
	esac
done

if [ -z "$config" ]; then
	config=evervolv
fi
if [ -z "$sourcedir" ]; then
	sourcedir=/backups/android/evervolv
fi

# Takes 1 arg: defconfig
build() {
	echo BUILDING $1
	make mrproper
	make $1
	time schedtool -B -n 1 -e ionice -n 1 make -j 6
	if [ $? -ne 0 ]; then
		exit 1
	fi
}

# Takes 2 args: source, destination
copy() {
	cp -v $1 $2
	if [ $? -ne 0 ]; then
		exit 1
	fi
}

if [ $passion -eq 1 ]; then
	build ${config}_mahimahi_defconfig
	copy drivers/net/wireless/bcm4329/bcm4329.ko $sourcedir/device/htc/passion/prebuilt/bcm4329.ko
	copy arch/arm/boot/zImage $sourcedir/device/htc/passion/prebuilt/kernel
	echo DONE ${config}_mahimahi_defconfig
fi

if [ $bravo -eq 1 ]; then
	build ${config}_bravo_defconfig
	copy drivers/net/wireless/bcm4329/bcm4329.ko $sourcedir/device/htc/bravo/prebuilt/bcm4329.ko
	copy arch/arm/boot/zImage $sourcedir/device/htc/bravo/prebuilt/kernel
	echo DONE ${config}_bravo_defconfig
fi

if [ $ss -eq 1 ]; then
	build ${config}_supersonic_defconfig
	copy drivers/net/wimax/SQN/sequans_sdio.ko $sourcedir/device/htc/supersonic/modules/sequans_sdio.ko
	copy drivers/net/wireless/bcm4329/bcm4329.ko $sourcedir/device/htc/supersonic/modules/bcm4329.ko
	copy drivers/net/wimax/wimaxdbg/wimaxdbg.ko $sourcedir/device/htc/supersonic/modules/wimaxdbg.ko
	copy drivers/net/wimax/wimaxuart/wimaxuart.ko $sourcedir/device/htc/supersonic/modules/wimaxuart.ko
	copy arch/arm/boot/zImage $sourcedir/device/htc/supersonic/prebuilt/root/kernel
	echo DONE ${config}_supersonic_defconfig
fi

if [ $inc -eq 1 ]; then
	build ${config}_incrediblec_defconfig
	copy drivers/net/wireless/bcm4329/bcm4329.ko $sourcedir/device/htc/inc/prebuilt/lib/modules/bcm4329.ko
	copy drivers/net/ifb.ko $sourcedir/device/htc/inc/prebuilt/lib/modules/ifb.ko
	copy arch/arm/boot/zImage $sourcedir/device/htc/inc/prebuilt/root/kernel
	echo DONE ${config}_incrediblec_defconfig
fi
