

.. |cbox|   unicode:: U+2610


.. _checklists:

##########
Checklists
##########

====================================
Running a Processed Setup
====================================

Prepackaged runs are common for testing SCHISM on a new system or rerunning a model 
from another user delivered as a bundle. In this case the user will have 
obtained a complete set up as a "tarball" (tar.gz) file or 
copies the run using the rsync command (don't use copy command `cp`). See :ref:`Linux hints <linux_hints>`.

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


======================
Simple Hindcast Runs
======================

|cbox| Choose run dates 
------------------------
See :ref:`hotstart section <choose_runtime>` on this topic


|cbox| Apply template to existing mesh
--------------------------------------

    |cbox| Clone BayDeltaSCHISM from GitHub. Get a fresh copy or `git stash` any changes. 
    
    |cbox| Note the git hash code or tag in a readme.

    |cbox| Copy BayDeltaSCHISM/templates/bay_delta to study preprocessing directory `mystudy/bay_delta`

    |cbox| Obtain an SMS .2dm or SCHISM hgrid.gr3 file (e.g. `bay_delta_111_prop605.2dm` and add it to bay_delta folder)

    |cbox| Change `main_bay_delta.yaml` by pointing the mesh_inputfile to the name of the mesh 

    |cbox| Make sure your flow transect file (flow_station_xsect.yaml) contains output you want

    |cbox| Invoke the preprocessor with the command: `$ prepare_schism main_bay_delta.yaml`

    |cbox| Copy the prepared items (.in, ,gr3, .ll, .prop, .nml) to the launch place. 

    
    

|cbox| Collect time series inputs
------------------------------------------

    |cbox| These steps are the two steps in BayDeltaSCHISM/bdschism/bdschism elev2d.bat, which you would adapt
    
        |cbox| download NOAA files for coastal stations at SF, Point Reyes, Monterey using download_noaa 
        
        |cbox| validate that the datum shown in the file is NAVD88 as this has been somewhat unpredictable
        
        |cbox| run the genelev2D, a utility that installs with `schimpy`. For details try genelev2D --help 

    |cbox| Adapt and run the multi_clip.py example in BayDeltaSCHISM/bdschism/bdschism to subset boundary/source data for your period.


|cbox| Hotstart (can be concurrent with barotropic)
---------------------------------------------------



|cbox| Nudging (can be concurrent with barotropic)
--------------------------------------------------



|cbox| Barotropic warmup
------------------------
    |cbox| interpolate_variables7 (or later) script to create uv3D.th.
    
    |cbox| move the uv3D.th to the study directory
    
    |cbox| delete all the files outputs/* or move /outputs to /outputs.tropic and create an empty /outputs


|cbox| Baroclinic simulation
----------------------------

    |cbox| finalize your station.in output request










