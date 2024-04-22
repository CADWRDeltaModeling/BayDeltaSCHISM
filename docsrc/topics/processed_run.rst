.. |cbox|   unicode:: U+2610

.. _existingrun:

#########################
Running a Existing Setup
#########################

Prepackaged runs are common for testing SCHISM on a new system or rerunning a model 
from another user delivered as a bundle. In this case the user will have 
obtained a complete set up as a "tarball" (tar.gz) file or copies the run using 
the rsync command (don't use copy command `cp`). See :ref:`Linux hints <linux_hints>`.

The steps are:

|cbox| Set up the environment and compile schism

|cbox| Untar the archived run

|cbox| If the atmospheric files are packaged separately, reestablish the linkage using the instructions in the readme file.

|cbox| Compile the model using instructions on the VIMS website or precompliled binaries for Windows\*

|cbox| Most clusters use a job manager and you submit to queue. Usually you need to adapt
    |cbox| schism.sh to point to executable and load dependencies
    
    |cbox| launch files such as launch.pbs (user name, number of cores and cpus per core, name of run)

|cbox| Create a directory called `outputs`

|cbox| Take care of any 'gotchas' such as making sure there is a directory named 'outputs' and that stack limits are disabled.

\* Windows is good for learning but not typical for full Delta runs




