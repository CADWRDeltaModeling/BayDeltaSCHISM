

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


.. |cbox|   unicode:: U+2610

======================
Simple Hindcast Runs
======================

|cbox| Choose run dates 
---------------------------------------------------
See :ref:`hotstart section <choose_runtime>` on this topic


|cbox| Apply template to existing mesh
--------------------------------------

    |cbox| Clone BayDeltaSCHISM from GitHub. Get a fresh copy or `git stash` any changes. 
    
    |cbox| Note the git hash code or tag in a readme.

    |cbox| Copy BayDeltaSCHISM/templates/bay_delta to study preprocessing directory `mystudy/bay_delta`

    |cbox| Obtain an SMS .2dm or SCHISM hgrid.gr3 file (e.g. `bay_delta_111_prop605.2dm` and add it to bay_delta_schism)

    |cbox| Change `main_bay_delta.yaml` by pointing the mesh_inputfile to the name of the 

    |cbox| Invoke the preprocessor with the command: `$ prepare_schism main_bay_delta.yaml`

    |cbox| Copy the prepared items (.in, ,gr3, .ll, .prop, .nml) to the launch place.



|cbox| Collect time series inputs
------------------------------------------

    |cbox| elev2d.bat
    
        |cbox| download NOAA files for coastal stations at SF, Point Reyes, Monterey
        
        |cbox| validate that the datum is NAVD88
        
        |cbox| runs genelev2D.py

    |cbox| multi_clip


|cbox| Hotstart (can be concurrent with barotropic)
---------------------------------------------------



|cbox| Nudging (can be concurrent with barotropic)
--------------------------------------------------



|cbox| Barotropic warmup
------------------------
    |cbox| interpolate_variables7 (or later) script to create uv3D.th.
    
    |cbox| move the uv3D.th to the study directory
    
    |cbox| delete all the files outputs/* or move /outputs to /outputs.tropic and create an empty /outputs















