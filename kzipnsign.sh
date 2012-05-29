#!/bin/bash

# copy kernel and modules from build directory to zip staging directory ($kdir/$name)
# zip it up and sign it and place in ($kdir/$zdir)
#
# to add another device: (MTD filesystem only atm)
# add a case the the switch there,
# then made an if statement to set the default name and message
#
# this script will only copy zImage and modules to the specified directory
# then zip that directory and sign it.

# for getopts
passion=0
bravo=0

while getopts "pbm:n:" opt; do
	case $opt in
		p)
			passion=1;;
		b)
			bravo=1;;
		m)
			updatemessage=$OPTARG;;
		n)
			name=$OPTARG;;
		*)
			echo fuck you ; exit 1;;
	esac
done

if [ $passion -eq 1 ]; then
	if [ -z "$updatemessage" ]; then
		updatemessage="NexusOne test kernel by drewis"
	fi
	if [ -z "$name" ]; then
		name=NexusOne-test-kernel-drewis
	fi
fi

if [ $bravo -eq 1 ]; then
	if [ -z "$updatemessage" ]; then
		updatemessage="HTCDesire test kernel by drewis"
	fi
	if [ -z "$name" ]; then
		name=HTCDesire-test-kernel-drewis
	fi
fi

# directories: should be prexisting like: $kdir/$sdir $kdir/$zdir
#
# common base directory (not the root of your build tree)
kdir=/home/drew/android/kernels
# location of staging area
sdir=test-kernels-staging
# location to put zips (appended to $kdir)
zdir=test-kernels
# location of testsign.jar
testsignloc=/usr/bin/testsign.jar
# name of zip file (minus .zip) defaults to YearMonthDay-Hour:Min
zipname=${name}-`date +%Y%m%d-%R`
# updater-script location
updaterscript=META-INF/com/google/android/updater-script

if [ ! -e $testsignloc ]; then
	echo Cant find testsign.jar; exit 1
fi
if [ ! -d $kdir/$sdir ]; then
	echo staging directory doesnt exist; exit 1
fi
if [ ! -d $kdir/$zdir ]; then
	echo final destination directory doesnt exist; exit 1
fi

echo copying..

if [ -e ./arch/arm/boot/zImage ]; then
	cp -v ./arch/arm/boot/zImage $kdir/$sdir/kernel/zImage
else
	echo cant find zImage; exit 1
fi

if [ -e ./modules.order ]; then
	modules=($(<./modules.order))
	modules=(${modules[@]#kernel?})
	for (( ii=0 ; ii < ${#modules[@]} ; ii++ )) ; do
		cp -v ${modules[$ii]} $kdir/$sdir/system/lib/modules/`basename ${modules[$ii]}`
		if [ $? -ne 0 ]; then
			exit 1
		fi
	done
else
	echo cant find the modules; exit 1
fi

cd $kdir/$sdir

echo creating updater-script..
cat > $updaterscript <<EOF
ui_print("");
ui_print("$updatemessage");
ui_print("AnyKernel Updater by Koush.");
ui_print("Extracting Modules...");
set_progress(1.000000);
mount("MTD", "system", "/system");
package_extract_dir("system", "/system");
set_perm_recursive(0, 0, 0755, 0644, "/system/lib/modules");
unmount("/system");
ui_print("Extracting Kernel...");
package_extract_dir("kernel", "/tmp");
ui_print("Preparing bootimg...");
set_perm(0, 0, 0777, "/tmp/dump_image");
set_perm(0, 0, 0777, "/tmp/mkbootimg.sh");
set_perm(0, 0, 0777, "/tmp/mkbootimg");
set_perm(0, 0, 0777, "/tmp/unpackbootimg");
run_program("/tmp/dump_image", "boot", "/tmp/boot.img");
run_program("/tmp/unpackbootimg", "/tmp/boot.img", "/tmp/");
ui_print("Making new bootimg");
run_program("/tmp/mkbootimg.sh");
ui_print("Writing new bootimg");
write_raw_image("/tmp/newboot.img", "boot");ui_print("");
ui_print("Done!");
EOF

if [ "`pwd`" != "$kdir/$sdir" ]; then
	echo change directory failed; exit 1
fi
if [ ! -x `which zip` ]; then
	echo no zip utility; exit 1
fi

echo zipping..
zip -r $kdir/$zdir/${zipname}.zip .

echo cleaning staging..
rm -f $updaterscript
rm -f kernel/zImage
rm -f system/lib/modules/*

cd $kdir/$zdir

if [ "`pwd`" != "$kdir/$zdir" ]; then
	echo change directory failed; exit 1
fi

echo signing..
java -classpath $testsignloc testsign ${zipname}.zip ${zipname}-signed.zip

echo removing unsigned zip..
rm -f $zipname.zip

echo done..
