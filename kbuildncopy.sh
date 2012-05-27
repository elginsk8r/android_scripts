#!/bin/bash
#
# build and copy kernels
#

if [ $# -eq 0 ]; then
	echo "Yikes. You must specify a board(s) (`basename $0`-h)"; exit 1;
fi

if [ -z $CROSS_COMPILE ]; then
	echo "You need to set your environment"; exit 1;
fi

if [ -z "`head -n1 ./Makefile | grep VERSION`" ]; then
	echo "What the hell. Are you in the right directory?"; exit 1;
fi

# Changed by getopts
passion=0
bravo=0
ss=0
inc=0
config="evervolv"
srcpath="/backups/android/evervolv"

print_help()
{
cat <<EOF
Usage:
	p : passion
	b : bravo
	s : supersonic
	i : inc
	t : use tiamat config
	c : set config prefix
	d : set destination directory (TOP of android tree)
	h : show this
EOF
}

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

# Takes 1 arg: destination
copy_kernel() {
	cp -v arch/arm/boot/zImage ${1}/kernel
	if [ $? -ne 0 ]; then
		exit 1
	fi
}

# Takes 1 arg: destination
copy_modules() {
	modules=($(<./modules.order))
	modules=(${modules[@]#kernel?})
	for (( ii=0 ; ii < ${#modules[@]} ; ii++ )) ; do
		cp -v ${modules[$ii]} ${1}/`basename ${modules[$ii]}`
		if [ $? -ne 0 ]; then
			exit 1
		fi
	done
}

while getopts "pbsithc:d:" opt; do
	case $opt in
		p) passion=1;;
		b) bravo=1;;
		s) ss=1;;
		i) inc=1;;
		t) config="tiamat";;
		h) print_help;;
		c) config=$OPTARG;;
		d) srcpath=$OPTARG;;
	esac
done

if [ ! -d $srcpath ]; then
	echo "Whoa. Specified android source directory doesn't exist"; exit 1;
fi

if [ $passion -eq 1 ]; then
	build ${config}_mahimahi_defconfig
	copy_modules $srcpath/device/htc/passion/prebuilt
	copy_kernel $srcpath/device/htc/passion/prebuilt
	echo DONE ${config}_mahimahi_defconfig
fi

if [ $bravo -eq 1 ]; then
	build ${config}_bravo_defconfig
	copy_modules $srcpath/device/htc/bravo/prebuilt
	copy_kernel $srcpath/device/htc/bravo/prebuilt
	echo DONE ${config}_bravo_defconfig
fi

if [ $ss -eq 1 ]; then
	build ${config}_supersonic_defconfig
	copy_modules $srcpath/device/htc/supersonic/modules
	copy_kernel $srcpath/device/htc/supersonic/prebuilt/root
	echo DONE ${config}_supersonic_defconfig
fi

if [ $inc -eq 1 ]; then
	build ${config}_incrediblec_defconfig
	copy_modules $srcpath/device/htc/inc/prebuilt/lib/modules
	copy_kernel $srcpath/device/htc/inc/prebuilt/root
	echo DONE ${config}_incrediblec_defconfig
fi

# Cleanup our mess
make mrproper
