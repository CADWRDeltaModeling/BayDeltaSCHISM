
.. _filesdirs:

###################################################################
Required Files, Directory Structure and Recommended Study Practices
###################################################################

New users often want to simply know an inventory of what files are required to get one basic model run going. 
This section provides that list. The section also addresses good practices for organizing a study that is reproducible, 
particularly one that spans several hypothetical alternatives. 

You will need to move data around. Users who are new to Linux or who are preprocessing on Windows and copying to Linux 
should check out the :ref:`linuxhints`, which covers several types of transfer 
as well as the indispensible topic of :ref:`symbolic links <symlink>` for organinzing files.

Required files and structure
============================

SCHISM launch directory structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A basic SCHISM launch directory has a top level directory, an `outputs` directory and a `sflux` directory::

  studyname    # See inventory below
  ├── outputs  # Empty, but required
  └── sflux    # Mostly generated links, see below

Launch directory
^^^^^^^^^^^^^^^^

The table is an inventory of files needed for a typical Bay-Delta SCHISM run. All the spatial inputs and driver files
are copied over by the preprocessor.  This inventory will inevitably occur if we change, say, the number or names of hydraulic structures. 
It will also be expanded when you use new modules, as indicated elsewhere in the user guide.
The items in bold are :ref:`symbolic links <symlink>`. These links follow the required SCHISM name but
point to more the similar but more detailed or version controlled names in brackets, choices of 
which would change between modeling periods or be modified in accordance with the rest of the user gude. 
Some files (`param.nml`,`bctides.in`,`vgrid.in`,nudging) are almost
always links. The links are currently created manually, although we are contemplating ways to make it more automatic.

Some of the most important files like the horizontal grid (`hgrid.gr3`) are covered extensively in this user guide.
Others are populated in very simple ways and seldom changed. For definitions, 
the intrested user can consult the `optional input page of the SCHISM Manual at VIMS <https://schism-dev.github.io/schism/master/input-output/optional-inputs.html>`_.

.. csv-table:: Files for a SCHISM Run
   :file: filesdirslist.csv
   :widths: 35,35,35,35,35,35
   :header-rows: 1

Output directory
^^^^^^^^^^^^^^^^

SCHI `outputs`. It will be empty but you need to make sure it is there. 


Atmospheric (sflux) directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The atmostpheric input (sflux) directory is a bit distinctive:

  * It is the only place we put :ref:`symbolic links <symlink>` to resources outside the immediate study directory
  * We share a common database across simulations from a similar era. These are on all our cluster file systems and we distribute on CNRA open data portal. Note that these often point to the original source as in the :ref:`example <examplesfluxdir>` below.
  * During the copying-over phase this directory initially only has two files:
  
    * sflux_inputs.txt which is boilerplate that never changes and 
  * make_links_full.py which contains links that are adjusted to populate all the symbolic links. 


So in the preprocessor you would have this::

  copy_resources:
  ...
  sflux/sflux_inputs.txt   # the boilerplate file
  sflux/make_links_full.py # adjusted to point to the atmospheric files


.. _examplesfluxdir:

Once you go to the study and run make_links_ful.py, the contents should look like this::

  /sflux
  ├── make_links_full.py
  ├── sflux_air_1.0001.nc -> ../../../data/atmos/baydelta_sflux_v20220916/baydelta_schism_air_20160427.nc
  ├── sflux_air_1.0002.nc -> ../../../data/atmos/baydelta_sflux_v20220916/baydelta_schism_air_20160428.nc
  ├── sflux_air_1.0003.nc -> ../../../data/atmos/baydelta_sflux_v20220916/baydelta_schism_air_20160429.nc
  ├── ...
  ├── sflux_inputs.txt
  ├── sflux_rad_1.0001.nc -> ../../../data/atmos/NARR/2016_04/narr_prc.2016_04_27.nc
  ├── sflux_rad_1.0002.nc -> ../../../data/atmos/NARR/2016_04/narr_prc.2016_04_28.nc
  ├── sflux_rad_1.0003.nc -> ../../../data/atmos/NARR/2016_04/narr_prc.2016_04_29.nc
  ...
  ├── sflux_rad_1.0001.nc -> ../../../data/atmos/NARR/2016_04/narr_rad.2016_04_27.nc
  ├── sflux_rad_1.0002.nc -> ../../../data/atmos/NARR/2016_04/narr_rad.2016_04_28.nc
  ├── sflux_rad_1.0003.nc -> ../../../data/atmos/NARR/2016_04/narr_rad.2016_04_29.nc
  ├── ...

Study layout
============

The overall structure of a study is discretionary. There are workflows that make transfer, sharing and reuse easier.
The examples here are starting points -- ultimately what you change depends on whether you have physical changes (e.g. restoration)
or forcing changes (years, operations). Your choices also may depend on whether you are prepping on Windows and moving 
to Linux (see example below) or doing everything on Linux.

It is recommended, and a standard in the Delta Modeling Section, that you isolate isolate the preprocessing template input (e.g. yaml) from the SCHISM native input (e.g. gr3). 

Here a possible study layout, commonly used in our group, for a simple study with one mesh, two sets of inputs time series
run for each of two widely separated years, so a total of four simulations (base_2010, base_2020, alt_2010, alt_2020)::

  /study_dir.
  ├───preprocessing           # bay_delta template, modified for study
  │   ├───simulation_inputs   # could stage your processed inputs here (Windows) or pipe preprocessor output to simulation directory\* 
  ├───hotstart_nudge
  │   │───20100312            # 2010 start years
  │   └───20200120            # 2020 
  ├───simulations 
  │   ├───base_2010           # schism launch directory for one alternative
  │   │   │───sflux  
  │   │   │───outputs
  │   │   └───outputs.tropic  # Generated during the barotropic warmup run and moved
  │   ├───base_2020           # schism launch dir for second alternative
  ...
  │   └───alt_2020
  └───th_files
  │   │───elapsed_2010        # Could collect and stage your elapsed time series here and move them (e.g. Windows) or do it in simulation directory 
  │   └───project_2010_base   # Preprocessed, datetime stamped files go here


\*The preprocessor has a key word `output_dir` which defaults to "simulation_input". You might consider changing this to the run directory but please don't use ".".


For a run that has two different physical domains (e.g. with and without restoration) studied over one period you might do this::

	study_dir
	├───base                     # schism launch directory
	│   ├───hotstart_nudging     # hotstarts/nudging files change with new grid or new period
	│   ├───outputs
	│   ├───preprocess           # bay_delta template input, output_dir=.. to move inputs parent dir 
	│   └───sflux                # links to outside database of atmospheric
	├───restoration
	│   ├───hotstart_nudging
	│   ├───outputs
	│   ├───preprocess
	│   └───sflux
	└───th_files
		├───elapsed              # staging point for /project and repo time series converted to elapsed
		└───project              # any study specific time series in datetime-stamped form 

