
.. _filesdirs:

###################################################################
Required Files, Directory Structure and Recommended Study Practices
###################################################################

New users often want to simply know an inventory of what files are required to get one basic model run going. 
This section provides that list. The section also describes practices for organizing a study that is reproducible, 
and spans several hypothetical alternatives. 

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
are copied over by the preprocessor.  This inventory will inevitably occur if we change, say, the number or names of hydraulic structures. It will also be expanded when you use new modules, as indicated elsewhere in the user guide.
The items in bold are :ref:`symbolic links <symlink>`. These links follow the required SCHISM name but
point to more the similar but more detailed or version controlled names in brackets, the specific
names of which evolve over time or are modified in accordance with the rest of the user gude. 
Some files (`param.nml`,`bctides.in`,`vgrid.in`,nudging) are almost
always links and are described in the section on the :ref:`barotropic warmup run <barotropic>`. The links are currently created manually, although we are contemplating ways to make it more automatic.

Some of the most important files like the horizontal grid (`hgrid.gr3`) are covered extensively in this user guide.
Others files are on more subjects like albedo, populated in very simple ways and seldom changed. 
For documentation, the interested user can consult the `optional input page of the SCHISM Manual at VIMS <https://schism-dev.github.io/schism/master/input-output/optional-inputs.html>`_.

.. csv-table:: Files for a SCHISM Run
   :file: filesdirslist.csv
   :widths: 35,35,35,35,35,35
   :header-rows: 1

Output directory
^^^^^^^^^^^^^^^^

SCHISM requires a directory called `outputs`. It will be empty at the beginning of the launch. 


Atmospheric (sflux) directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The atmostpheric input directory is called `sflux`. It is a bit distinctive:

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

Input/Output Units
======================

SCHISM input and output files are described in the `SCHISM manual <https://schism-dev.github.io/schism/master/index.html>`_, however the input file units and output file units are not always clear. The following table summarizes the units for the most commonly used input and output files.

.. list-table:: Common SCHISM Input/Output Units
  :header-rows: 1
  :widths: 25 25 50 50

  * - Variable
    - Unit
    - Relevant Inputs
    - Relevant Outputs
  * - Water Surface Elevation
    - m (positive up)
    - elev2D.th, elev.ic, uv3D.th.nc
    - staout_1, out2d_*.nc
  * - Bathymetry
    - m (positive down)
    - hgrid.gr3
    - out2d_*.nc
  * - Velocity (u, v)
    - m/s
    - sflux_air_1.*.nc (wind speed), uv3D.th.nc (water velocity)
    - horizontalVelX_*.nc, horizontalVelY_*.nc, staout_3 (wind u), staout_4 (wind v), staout_7 (hydro u), staout_8 (hydro v), staout_9 (hydro w)
  * - Salinity
    - PSU
    - SAL_*.th, SAL_nu.nc
    - salinity_*.nc, staout_6
  * - Water Temperature
    - °C
    - TEM_*.th, TEM_nu.nc
    - temperature_*.nc, staout_5
  * - Generic Tracer
    - 1 (unitless. volumetric fraction)
    - gen_*.th
    - 
  * - Air Temperature
    - K (2m AGL)
    - sflux_air_1.*.nc
    - N/A
  * - Specific Humidity
    - 1 (2m AGL)
    - sflux_air_1.*.nc
    - N/A
  * - Atmospheric pressure
    - Pa (reduced to MSL)
    - sflux_air_1.*.nc
    - staout_2
  * - Precipitation
    - kg/m²/s (flux)
    - sflux_prc_1.*.nc
    - N/A
  * - Shortwave radiation
    - W/m² (long- and short-wave)
    - sflux_rad_1.*.nc
    - N/A
  * - Evaporation
    - kg/m²/s (flux)
    - N/A
    - out2d_*.nc
  * - Suspended Sediment Concentration (ssc)
    - kg/m³
    - SED_hvar_[class].ic (initial condition for ssc for each size class, in kg/m³), bed_frac_[class].ic (initial bed composition fraction for each size class, unitless), bedthick.ic (initial bed thickness, in m), imorphogrid.gr3 (scale applied to depth change at each node, unitless, used only when imorpho==1).
    - sedConcentration_[class]_*.nc

The geospatial projection uses NAD83 UTM Zone 10N with horizontal coordinates in meters. Vertical coordinates are against NAVD88. Time is in seconds since whichever start date specified in the param.nml.