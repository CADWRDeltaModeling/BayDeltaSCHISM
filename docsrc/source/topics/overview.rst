

##################################
Checklists for Simple Examples
##################################

====================================
Running a Completely Processed Setup
====================================

Benchmark runs are recommended when using SCHISM on a new system or when setting up 
a new machine. In this case the user will have obtained a complete set up as a "tarball" (tar.gz) file or 
copies it using the rsync command. 

The steps are:

* Set up the environment and compile schism (on Windows we provide binaries, but this is not an efficient environment for running the model).
* Untar the archived run
* If the atmospheric files are packaged separately, reestablish the linkage using the instructions that we provide in a typical readme** file.
* Compile the model using instructions on the VIMS website or precompliled binaries for Windows (not typical for full Delta runs) 
* Most clusters use a job manager or queue. We have sample schism.sh shell scripts and PBS launch files that borrow from our own systems, but you may need to find instructions that suit your pattern.
* Take care of a few typical 'gotchas' such as making sure there is a directory named 'outputs' and that stack limits are disabled.

While we can provide some support and answer some questions, the details differ from machine to machine. Please note that when you copy runs you should use the rsync command on linux not the generic copy command 'cp'.

======================
Simplest Hindcast Runs
======================

In this case, simulation is within the historical database we provide in our repository for SCHISM
, which starts Oct 2006. We are not, however, assuming 

Scoping
-------
The main scoping questions are:
# What is the period of interest?
# Does the simulation require grid modification?
# Where will you do the run?

Obtain materials
----------------
See the 

Collect Spatial Inputs
--------------
# Preprocess the grid using templates and schimpy
# 


# Prepare elevation boundary
Subset the historical inputs for run period
Subset channel depletions for run period
Create appropriate nudging file for assimilating data
Perform barotropic run and extract ocean boundary velocity















