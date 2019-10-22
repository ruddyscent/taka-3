# HowTo: Install Wolfram Eigine on Jetson

As shown at ‘[Launching Today: Free Wolfram Engine for Developer](https://writings.stephenwolfram.com/2019/05/launching-today-free-wolfram-engine-for-developers/](https://writings.stephenwolfram.com/2019/05/launching-today-free-wolfram-engine-for-developers/),’ Wolfram Engine is licensed as free for developers and home users. If the result remains as open, we can use Wolfram Engine without any cost. However, the distributed version is the lack of ARM architecture. 

Fortunately, ARM version of Wolfram Engine is distributed in the RPi image. Copy whole /usr/Wolfram directory on Raspberry Pi to an external storage, and mount it to /mnt on Jetson. Then:

```console
$ cd /mnt
$ sudo cp Wolfram/ /usr/local/
$ cd /usr/local/bin
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/math ./
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/mathematica ./
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/Mathematica ./
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/MathKernel ./
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/mcc ./
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/wolfram ./
$ sudo ln -s ../Wolfram/WolframEngine/12.0/Executables/WolframKernel ./
$ sudo ln -s ../Wolfram/WolframScript/bin/wolframscript ./
```

The mathematica executable fails to recognize the operating system and returns an error. Because Mathematica supports arm64, there may be a trick to deceives Mathematica into believing the OS is one of RPi.

```console
$ mathematica
mathematica cannot determine operating system.
```

This response is caused by the result of `uname -s` and `uname -m`:

```console
$ uname -s
Linux
$ uname -m
aarch64
```

This result affects the variable, `$SystemIDList`. Add `SystemIDList="Linux-ARM"` at the first part of the scripts: `/usr/local/Wolfram/WolframEngine/12.0/Executables/{math,mathematica,Mathematica,MathKernel,mcc,wolfram,WolframKernel}`. For example,

```diff
--- math.orig    2019-10-11 17:51:32.682505575 +0900
+++ math    2019-10-11 17:30:14.365039519 +0900
@@ -3,7 +3,7 @@
 #  Mathematica 12.0.1 Kernel command file
 #  Copyright 1988-2019 Wolfram Research, Inc.

-
+SystemIDList="Linux-ARM"

 #  Make certain that ${PATH} includes /usr/bin and /bin
 PATH="${PATH}:/usr/bin:/bin"
```

Therefore, we can overwrite this variable, then the above error disappears. However, another error occurs:

```console
$ cd /usr/local/Wolfram/WolframEngine/12.0/SystemFiles/Kernel/Binaries/Linux-ARM
$ ./WolframKernel
-bash: /usr/local/Wolfram/WolframEngine/12.0/SystemFiles/Kernel/Binaries/Linux-ARM/WolframKernel: No such file or directory
```

According to the result of `file` and the following link, the problem is about the 32-bit executable on a 64-bit system:

https://askubuntu.com/questions/133389/no-such-file-or-directory-but-the-file-exists

```console
$ cd /usr/local/Wolfram/WolframEngine/12.0/SystemFiles/Kernel/Binaries/Linux-ARM
WolframKernel: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), dynamically linked, interpreter /lib/ld-, for GNU/Linux 3.2.0, BuildID[sha1]=427eb103e891902385e4d7fc45a08116b7f074d7, stripped
```

A solution is addressed at https://forum.armbian.com/topic/4764-running-32-bit-applications-on-aarch64/.

```console
$ sudo dpkg --add-architecture armhf
$ sudo apt update
$ sudo apt install libc6:armhf libstdc++6:armhf libgmp10:armhf zlib1g:armhf libglu1-mesa:armhf libpng16-16:armhf libfontconfig1:armhf libpixman-1-0:armhf libportaudio2:armhf libuuid1:armhf libgtk3-nocsd0:armhf libdbus-1-3:armhf
```

When executing Mathematica frontend, we encounter a `libGL` related error. However, the frontend works well in spite of the error:

```console
$ mathematica 
libGL error: No matching fbConfigs or visuals found
libGL error: failed to load driver: swrast
```

![IMAGE](/Users/kwchun/Workspace/taka-3/jetson/WolframEngine/image/activation.png)

Automatic Web Activation seems that it does work. However, the manual activation works well. Using Activation Key, MathID, and password, we can activate our copy of Mathematica:
![IMAGE](/Users/kwchun/Workspace/taka-3/jetson/WolframEngine/image/welcome.png)
![IMAGE](/Users/kwchun/Workspace/taka-3/jetson/WolframEngine/image/notebook.png)

## Limitations

1. The license for Free Wolfram Engine is not working.
2. Automatic Web Activation is not working.
3. The GPU acceleration is not supported.
4. CUDA is not supported.
