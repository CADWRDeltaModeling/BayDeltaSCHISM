

.. |cbox|   unicode:: U+2610


##################################
Overview of a Bay-Delta SCHISM Run
##################################


This section of the User Guide gives an overview of the  tasks you might need 
to perform to set up a basic hindcast run on the existing grid for an arbitrary but recent run period. 
The tasks and concepts are further developed in other sections of the user guide. 

The simplified working assumptions here are:

  #. The run is being done on  an existing mesh.
  #. The selected run dates are within the project's supported historical period of 2008-2024.
  #. The variables of interest are water levels, velocity, temperature and salinity.

Spatial inputs and temporal inputs are somewhat independent. New users should go over at least this page before they start doing runs. If you are an accomplished modeler, you probably know what you are looking for -- but you should still
be alert for a few number of concepts (nudging, hotstart, barotropic-baroclinic sequence) that use
nomenclature or tactics that are potentially a bit new.

For more accomplished users, repeating the thicket of details is tedious. We are starting to consolidate the material to :ref:`task specific checklists <checklists>`. 




=====================
Grid and Spatial Data
=====================

`Spatial data` refers to distributed inputs like the grid elevations, roughness, background diffusivity and vegetation density.  We disseminate and modify Bay-Delta spatial data by means of our `templates` and `preprocessor` system. 

Why do it this way? Our applications are not static. We need to quickly reapply parameters, structures, etc as meshes change, restoration regions are incorporated or scenarios change. SCHISM native input formats are specified in terms of model topology, using node and element indexes. (see the `I/O section of the SCHISM online manual <https://schism-dev.github.io/schism/master/input-output/overview.html>`_). The spatial files can be visualized, but the system is fragile and hard to organize when you start to make changes.

If you aren't doing much with the grid, it is possible to grab an entire :ref:`existing run <existingrun>`: and modify a few boundary conditions to suit a period of interest using the instructions outlined below. The approach suits certain study contexts where the boundary forcing is the only things that varies across alternatives. It is also possible to re-process only a small number of files. However, our pre-processed runs are not updated as often and as rigorously as the GitHub distribution. This workflow is more the exception than the rule.

The BayDeltaSCHISM repo is self-contained for spatial data except for some large files:
 * Only a sample of mesh files (called something like hgrid.gr3) is distributed. Others are available on CNRA Open Data Portal
 * If you are populating or changing the mesh with elevation data, bathymetry is distributed on CNRA Open Data Portal
 * Vegetation data from the UC Davis Ustin lab is distributed on CNRA Open Data Portal.

Note that we are committed to providing these materials, they just don't play well with GitHub or some of the large data extensions.

Templates
^^^^^^^^^
To get an idea what we mean by a template, you can take a look at a template in the in the `repo template directory <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/templates/bay_delta>`_. When you clone the `GitHub repo <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/>`_ you get the template.

Our that our templates express the domain layout and parameters in terms of geophysical coordinates, datastructures and formulas. Many template files are based human readable text (`yaml <https://www.redhat.com/en/topics/automation/what-is-yaml>`_). The differences in how things are generated are easier to spot and keep coordinated -- the items in a template for one mesh will work on the next mesh except in the immediate neighborhood of any changes. Of course visualizing distributed parameters is also a great idea and also gives a valuable intuition.


Preprocessor
^^^^^^^^^^^^

In order to convert from our templates to SCHISM native inputs we use the :external:ref:`schimpy preprocessor <preprocessor>`, which is installed when you install our recommended python packages. The default usage is usually as simple as:

.. code-block:: console

   $ prepare_schism main_bay_delta.yaml

If you just want to modify a few things you can do that with a stripped down input file. Once you are done generating the inputs you will need to copy over files to the ultimate launch directory. See :ref:`copyfiles`. 



===================
Time-dependent data
===================

When you change time periods, you will need to attend to the following:

  #. Generate the ocean water level boundary condition input file (elev2D.th.nc [REF]) using two coastal stations for your period of interest.
  #. Subset the inflow/outflow boundary conditions (flux.th, salt.th, temp.th) for the model period and translate to elapsed time. Inputs for the standard boundary locations from (2008-present) are distributed with the package in the Bay-DeltaSCHISM/data/time_history folder.
  #. Subset source and sink data. Again, data for the standard sources and sinks (from channel depletion models) come with the package.
  #. Link from your simulation to atmospheric files for wind, radiation, etc. These are one of the "big" datasets. They are not included but we offer them for download on the CNRA open data portal (see the :ref:`getstarted` page). In our workflow, we don't copy them into every run. The atmospheric inputs reside in a common file location on the cluster and we have a script to create links from the launch directory structure to the data. 
  #. Create a `hotstart.in.nc` file for the initial condition. This is SCHISM/coastal nomenclature for a file that contains a complete initial condition or restart if you pause midway. Some models call it `restart`. A much more complete description can be found in the [HOTSTART REF] section.  
  #. Create `nudging` files for salinity and temperature as required. `Nudging` refers to Newtonian Relaxation, a crude form of data assimilation. We use nudging near the coastal boundary to provide a sponge-like boundary condition for salinity and temperature. In hindcasts, we also use nudging during the spin up process, injecting observed data in the opening 2-3 weeks of simulation. Relative to just a hotstart file (which requires a lot of interpolation), this is a fast and accurate way to initialize the model. This latter form of nudging is only for warm up -- it should not be used during validation or evaluation periods or when alternatives are being compared. 

The repository is 


.. _time-or-space:

==========================================
Files that Change with Both Mesh and Dates
==========================================

There are a small number of files that are both time and start-date sensitive. These are the files that are used to initialize the model for a particular date (hotstart.in.nc) and the so-called `nudging` files that are used to enforce a soft boundary on the coast for temperature and salt. 

Additionally if you change the number or location of boundaries (a spatial input) you will have to make corresponding changes in the boundary conditions for fluxes and traces.

The BayDeltaSCHISM repo is mostly self-contained for temporal data 
except for some large spatiotemporal files:
 * Atmospheric data are disseminated on CNRA Open Data Portal
 * Prepared coastal boundary temperatur and salt data for nudging [REF] is disseminated on CNRA Open Data Portal. 
 * Vegetation data from the UC Davis Ustin lab is distributed on CNRA Open Data Portal.


=================================================
Driver Files (param.tropic.nml, param.clinic.nml)
=================================================

These \*.nml files are the main control files for running SCHISM and provide algorithm parameters. 
We don't recommend changing the driver files initially, but you can expect to need the following for 
basic workflows:

  * specify the run start date and number of days (nday) 
  * specify `ihot`, the type of initialization. We use cold starts (ihot=0), hot starts from t=0(ihot=1) and restarting (ihot=2) at various points in our workflow. See [REF]
  * check the nudging switches
  * specify binary outputs
  
You will also note that there are two files, one with baroclinicity ('clinic) and one with only barotropic pressure ('tropic). When we do studies we often do a preliminary pass with a 2D model to establish more well behaved boundaries. The need for this is a frequent topic of interest for new users. There is a writeup [REF]. The topic is worth a quick read, if only to make the workflow and alternatives more clear. 


===============================
Other Nomenclature and Concepts
===============================

Besides the high performance platform there are a few concepts or bits of nomenclature that are especially new to Bay-Delta SCHISM users:

.. _tropic:

*barotropic warm up:*
At the beginning of a new study, or for each alternative with large landscape or sea level differences, we do a preliminary simulation in barotropic mode (in 2D no density, very diffusive settings). The only purpose of this run is to extract a reasonally dampened ocean boundary condition for the rest of the study. The output of this step is a file called `uv3D.th.nc`. For more information ... 

*hotstart:*
This is the name of the file used for initializing the model or restarting it to change inputs or recover from an error. 

*hydraulic structures:*
This is the term used for gates and barriers. 

*nudging:*
Nudging is a crude form of data assimilation that is used either to generate a sponge-like boundary condition on the coastal boundary or to aid with spin-up of the model in a hindcast.


==============
Final Assembly
==============

We do our work on clusters, but we are evenly divided between folks who prep on Windows and others who prep on Linux.

As you gather up your run, generally the work flow looks like this:

  #. Run the preprocessor 
  #. Copy the resulting spatial inputs over to Linux with a tool like WinSCP
  #. Subset the time boundary conditions (\*.th) and copy to the same directory (:ref:`copyfiles`)
  #. Remotely log into the head node of the cluster and submit to the job management system. For more on the layout of a typical cluster and how you log in see [REF]











