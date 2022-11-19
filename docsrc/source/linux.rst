***********************
Linux Hints for SCHISM
***********************

.. contents:: Contents
   :depth: 3




Using Linux from Windows
========================

You will need tools to:

- connect to the Linux server that serves as a gateway, sometimes called a *server* or on clusters or supercomputers often called the *head node*. 
- for graphical applications with windows like browsers and some text editors, you may need something called "XWindow Emulation". 
- A method to copy files back and forth fast, usually with a secure (ssh) method
- often you will want to set up an efficient text editor (Visual Studio Code) and VisIT both of which
adopt a client-server approach to viewing or working on things in Windows that are located on Linux (the server) 


Basic connection
-----------------
The simplest tools is PutTy, which can also handle passwordless login using rsa tokens. MobaXTerm is an all-in-one tool that can also handle this task (??).

Copying files
-------------
Copying between Windows and Linux is best done using WinSCP, which piggybacks on Putty. Two side benefits
of WinSCP is that you can use your windows-side text editor on Linux-side files just by clicking, 
though this is only going to work well if the file is a managable size. The copies are faster than
other tools and the filter options are very efficient at narrowing down what you are looking at in a directory with hundreds of fi. Two particularly convenient filters are these: 

- sta*;flow*;flux*   # For viewing station outout files and output requests
- *.gr3;*.ic;*.in;*.ll;*.prop;*.nml;*.2d;*.3d;*.clinic;*.tropic;readme*;make_links* | nlayer*.gr3;split_quad.prop

XWindow Emulation
-----------------
You can do this with MobaXTerm, Xming, vcxsrv. These tools provide an engine to emulate graphics.
These are free products. There may be commercial alternatives such as Hummingbird Exceed. XWindows
can be slow with some remote servers or connections, and that may not be something your emulation software can speed up.
For text editing this is the reason a lot of us use VS Code, which uses a client-server approach where
the graphics are actually done locally on windows.

All-in-one: MobaXTerm
----------------------
MobaXTerm provides an all-in-one approach to the above tasks, but note that it is markedly inferior
at some of them. In particular, it is orders of magnitude slower copying files because it uses a slower protocol and it 
lacks good filtering so you have to wait for it to scan directories with thousands of files. As with 
WinSCP, it can open a file for editing using local Windows editors, but since the copying is slower the
restrictions will be a bit more severe. Anyhow, it is an interesting option and does basic terminal
work and connections well.
 


Copying a Run Safely
====================
Do NOT use the linux copy command 'cp' to copy a run. A considerable amount of information, particularly symbolic links, will be lost. Instead use rsync:

- Basic command: `rsync -avz /path/to/original_sim/ /path_to_dest/

  - The trailing slash on original_sim/ is important. There are many explanations online: search 'rsync trailing slash'.
  - Symbolic links will be preserved.  
  - If you want to move rather than copy, use --remove-source-files
  - Usually, you will want to void copying heavy outputs with `--exclude` option. You can stack them. Examples are:

    * `--exclude='outputs*'` omits any directory starting with outputs, in which case you will have to create a new one.
    * `--exclude='outputs.tropic*'` omits an extra alternative directory, which you may have created and moved to a new name.
    * `--exclude='outputs/*.nc'` leaves staout_1 through staout_9 and flux.out, needed for restarting using ihot=2.
    * `--exclude='outputs/nonfatal*'` omits the nonfatal error messsages, which can be big but will be overwritten by new runs.

- Change the name of the run in launch.pbs files to something short and informative. 
- Change the contact email in launch.pbs.
- At this point if the prior simulation was runable the new one should be. 

Special Case: Remote Computer Using RSA Keys
--------------------------------------------
We run into this case a lot when copying data from, say, an Azure virtual cluster 
in a situation where password authentication is not used.

`rsync -e 'ssh -i ~/.ssh/id_rsa_name' -avz myname@10.7.240.8:/shared/home/myname/simulations/sim_name/ local_sim_name/ --exclude='outputs.tropic*' --exclude='outputs/*.nc'`


Symbolic links
=================

Archives and Tarballs
=======================

Essential commands in a SCHISM context
======================================

Countless Linux introductions are available online, including some excellent `cheat sheets like this <https://files.fosswire.com/2007/08/fwunixref.pdf>`_. Once you know the commands or vocabulary, it is easy to get more information. You will need `cd`, `ls`

cd some_dir
    Go to the named directory, which may be relative or absolute. Consider pushd some_dir instead if you want to go somewhere temporarily such as to recompile, and then return (with popd)

df -h 
    List total disk use and availability (ie, is there room for a run?)
 
du -h | sort -n -s
    List disk usage in human readable form starting at the point where launched  and "pipe" the output to the sort command which lists the results from large to small (ie, how much room have I used here)

find . -name 'hotstart_000???_*.nc'
    Find files that match the pattern, with ? matching a single character. Numerous options to take action like deleting. 

grep
    Finds a word or phrase in the contents of files or a string. For instance, `grep nday param*.nml` will give you all the lines with nday in it in all the files matching the wildcard param*.nml (check the end day; use start_ to get the start year, month, day).  

ls -al
    This variant of the  file listing command `ls` shows dates as welll as symbolic link targets relationships
    
pwd
    Name of the current directory

scp 
    Another fast, secure copying tool based on ssh.
    
tail -n 15
    Look at the last 15 lines of a file, default 10. Add -f to keep updating, for instance do this with outputs/mirror.out to check if run is chugging along.


  