
.. _bdschinstr:

Vignette: Hindcast Bay Delta SCHISM at Delta Modeling Section with Preprocessor
===============================================================================

The process for starting a Bay Delta SCHISM run from scratch involves some pre-processing work on a Windows machine using the schimpy library (https://github.com/CADWRDeltaModeling/schimpy).

You'll want to have a conda environment which has the latest version of schimpy in it. For this example that environment is called 'schism'.

Windows
******************************

#. Clone the Bay Delta Schism repository to your Windows machine (ex: D:/schism/bdsch_scratch)

   * git clone https://github.com/CADWRDeltaModeling/BayDeltaSCHISM.git (creates a BayDeltaSCHISM folder within bdsch_scratch)
   * if already cloned, then pull updates to the repository

   .. code-block:: console

      git pull

#. Create a directory on Windows where you'll build model inputs ("./baydeltainputs") and copy the following files into it:

   * From "./BayDeltaSCHISM":
      * "./BayDeltaSCHISM/templates/bay_delta" folder contents
      * "./BayDeltaSCHISM/data/flow_station_xsects.yaml" 
      * "./BayDeltaSCHISM/data/stations" folder contents
      * "./BayDeltaSCHISM/scripts/multi_clip.py"
   * You'll need a .2dm file for the pre-processor, copy this into the baydeltainputs folder
   * Need launch.pbs files
      * launch.tropic.pbs
      * launch.clinic.pbs 
         .. warning::

            These files don't exist somewhere publicly available yet

   * schism.sh file
      .. warning::

         These files don't exist somewhere publicly available yet

   * Download `noaa_stations.txt`_
      .. _noaa_stations.txt: https://github.com/CADWRDeltaModeling/dms_datastore/blob/master/dms_datastore/example/noaa_stations.txt
   
#. Edit input files

   * If modifying the bathymetric data create a copy of 'dem_4.2_cc.yaml' and rename it
      * correctly locate the Dutch Slough DEM
      * Suppy additional DEM data
   * main_bay_delta.yaml
      * change mesh_inputfile: parameter to match the .2dm file you copied into the project folder
      * check that the vgrid: section contains a vgrid_version: variable set to the SCHISM version being used (5.8 or 5.10)
         * ex: vgrid_version: '5.10' # Note that quotation marks are necessary
      * If you've modified the bathymetric data, then update the dem yaml file to that .yaml file
      * Add these lines above the sav\_*.gr3 specifications:
      
         .. code-block:: text
         
            sav_cd.gr3: 
               default: 1.13

   * sav_density.yaml
      * change "W:/sav" to "//nasbdo/Modeling_Data/sav" for all cases where "W:/sav" is found
   * multi_clip.py 
      * Set the following variables according to your simulation start date (this example uses May 1, 2009)
         
         .. code-block:: text
         
            start=dtm.datetime(2009,5,1) 
            bds_home = "<BAYDELTASCHISM REPOSITORY LOCATION>"

   * launch.tropic.pbs & launch.clinic.pbs
      * #PBS -N <SIMULATION NAME>
         * ex: #PBS -N v112_demo
      * #PBS -M <USER EMAIL>, <USER>@localhost
         * ex: #PBS -M jane.doe@water.ca.gov,janedoe@localhost

   * schism.sh
      * Set the last line to be the location of your compiled pschism build followed by the number 10

   * param.nml.tropic & param.nml.clinic
      * Set start_year, start_month, start_day, start_hour, and utc_start according to the simulation start date
      * Edit byear, eyear, bmonth, emonth, bday, eday to have the full date range of the simulation
      * Edit rnday for runtime

   * make_links_full.py
      * check src_dir and src_dir_narr 

#. Run files:

   * multi_clip.py
      * Creates a list of .th files necessary for the run to execute found in simulation directory
   * In a conda environment with schimpy installed, go to simulation directory and run:
   
   .. code-block:: console
    
       prepare_schism main_bay_delta.yaml

   * Create station inputs using:

   .. code-block:: console
    
       station --station_db station_dbase.csv --subloc_db station_subloc.csv --request all

#. Create Hotstart and Nudging datasets

   * If you're only running a 2D/Barotropic simulation then you don't need to create these files!

   * Create a sub-folder (./baydeltainputs/hotstart) and copy files:
      * hotstart_nudging_data.py 
      * hotstart_lat.py 
      * clean_nudge.py 
      * clean_polaris.py 
      * hotstart.yaml
      * nudging.yaml 
      * nudge_roms/nudge_obs_roms.yaml 
      * nudge_roms/roms_nudge.py 
      * shapefile/RegionsPolygon.*
      * USGS_polaris_station_locations_xy.csv 

   .. warning::

      These files don't exist somewhere publicly available yet

   * Download Polaris \*.csv data from the USGS data query https://sfbay.wr.usgs.gov/water-quality-database/
      * Since the hotstart generates based on a USGS cruise, check "//nasbdo/Modeling_Data/usgs_cruise/cruise_inventory.csv" to see what dates are available. You'll want your hotstart date to be near an available cruise date
      * Go to year, show all entries, and export data
      * Save as: hotstart\USGS_2009_saltemp.csv (where 2009 is whichever year you've downloaded)
      * Run *clean_polaris.py* or some other QA/QC on the USGS_2009_saltemp.csv file
         * This creates a copy of the file with _edit.csv as the extension

   * Edit files:

      * hotstart_nudging_data.py
         * Change nudging time to desired model run length
            * ex: nudgelen=days(60)
         * Set start time
            * ex: t0=pd.Timestamp(2009,5,1)
      * hotstart.yaml  
         * Point to correct hgrid and vgrid _input files (../hgrid.gr3 & ../vgrid.in.3d generated from prepare_schism)
         * For all data using "extrude_casts:" method, replace with ./USGS_2009_saltemp_edit.csv
         * For all data using "obs_points:" method, replace with "./hotstart_data_{temperature/salinity}.csv" and variable: {temperature/salinity} depending on whether looking to set temperature or salinity. These files will be generated with  hotstart_nudging_data.py
         * Set vgrid_version='5.10' # Note that the quotation marks are important
      * nudging.yaml
         * Change run days to whatever number of days you want the internal points to be nudged towards observation data
            * ex: rnday: 7
         * Set vgrid_version='5.10'
         * Change temperature/salinity data: ./nudging_data_{temperature/salinity}_edit.csv based on which variable you're setting
      * nudge_roms/nudge_obs_roms.yaml
         * start_date: 2009-05-01 (or whatever your start date is)
         * rnday: 60
         * Point to correct hgrid/vgrid files (../hgrid.gr3 & ../vgrid.in.3d)
      * hotstart_lat.py
         * Set vgrid_version='5.10'
         * Set hgrid and vgrid to same filenames as hotstart.yaml (../hgrid.gr3 & ../vgrid.in.3d)
         * Set ini_date to correct start date
         * Set hotstart_fn to appropriate filename (ex: hotstart.20090501.nc or whatever your start date is)

   * Run files:

      * You'll want to run these files in a conda environment that has dms_datastore installed (There's an existing environment.yaml file which will set this up for you)
      * This might be better to run on Linux/HPC4 so that your machine doesn't interrupt the files and corrupt the .nc files these scripts produce

      .. warning::

         The environment.yaml file does not exist somewhere publicly available yet 

      * hotstart_nudging_data.py
         * Takes quite a long time, if the time period hasn't changed then this step does not need to be repeated
         * Need to QA/QC hotstart and nudging csv data 
            * Run clean_nudge.py to create nudging_data_{temperature/salinity}_edit.csv

      * hotstart.py
         * Creates:
            * salinity_nudge.gr3
				* temperature_nudge.gr3
				* hotstart.20090501.nc
				* SAL_nu_obsroms.nc

      * nudge_roms/roms_nudge.py
         * Takes a very long time. If the time period *or* grid hasn't changed then this step does not need to be repeated
         * Rename SAL_nu_obsroms.nc and TEM_nu_obsroms.nc to be SAL_nu_roms.nc and TEM_nu_roms.nc

   * Copy output files out to the main simulation folder (./baydeltainputs)
      * hotstart/TEM_nu_obsroms.nc
      * hotstart/SAL_nu_obsroms.nc
      * hotstart/temperature_nudge.gr3
      * hotstart/salinity_nudge.gr3
      * hotstart/hotstart.20090501.nc
      * hotstart/hgrid.nc
      * hotstart/nudge_roms/TEM_nu_roms.nc
      * hotstart/nudge_roms/SAL_nu_roms.nc

Linux
******************************
        
#. Create the folder where you will be running the model (ex: /scratch/dms/{username}/schism/bdsch_scratch_demo)

   * from your Windows machine, copy "./baydeltainputs" contents into your Linux model folder (bdsch_scratch_demo) 
   
Barotropic
-----------------

#. Make symbolic links for sflux files

   	* mkdir sflux
		* cd sflux
		* python ../make_links_full.py
		* cd ..

Then you'll need a sflux_inputs.txt file within the sflux folder

.. warning::

   The sflux_inputs.txt file does not exist somewhere publicly available yet 

#. Create elev2d.th.nc file. Run in Linux conda environment with dms_datastore and schimpy installed:

   .. code-block:: console

      download_noaa --syear 2009 --eyear 2009 --param water_level noaa_stations.txt 

   * Adjust start and end year based on simulation period

   .. code-block:: console

      gen_elev2d --outfile elev2D.th.nc --hgrid=hgrid.gr3 --stime=2009-5-1 --etime=2009-7-1 --slr 0.0 noaa_download/noaa_pryc1_9415020_water_level_2009_2010.csv noaa_download/noaa_mtyc1_9413450_water_level_2009_2010.csv

   * Again, be mindful of the years in the filenames as well as the stime and etime inputs

#. Make symbolic links for the Barotropic run

   .. code-block:: console

      ln -sf bctides.in.2d bctides.in
      ln -sf vgrid.in.2d vgrid.in
      ln -sf msource_v20220825.th msource.th 
      ln -sf vsource_20220825_nows_leach1.th vsource.th
      ln -sf vsink_20220825_nows_leach1_sscd1.5.th vsink.th
      ln -sf TEM_1.th temp.th
      ln -sf SAL_1.th salt.th
      ln -sf param.nml.tropic param.nml
      ln -sf launch.tropic.pbs launch.pbs

   #. Make the outputs directory

   .. code-block:: console

      mkdir outputs

   #. Run barotropic model

   .. code-block:: console

      qsub launch.pbs

This will run the Barotropic model without nudging or hotstart data and then you will use the Barotropic results to generate a flow boundary at the ocean in order to stabilize perturbations in the model.

Baroclinic
---------------

This needs to follow the completion of a Barotropic simulation in order to create the ocean boundary flows. At this stage the hotstart and nudging files created in the Windows portion are used on the temperature and salinity fields.

   #. Rename the *outputs* folder to *outputs.tropic* and create a new empty *outputs* folder

   #. Create uv3d.th.nc

      * In *outputs.tropic*
         * Copy *interpolate_variables.in* to *outputs.tropic* folder
         
         .. warning::

            The interpolate_variables.in file does not exist somewhere publicly available yet 

         * Create symbolic links
         
         .. code-block:: console

            ln -sf ../hgrid.gr3 bg.gr3
            ln -sf ../hgrid.gr3.fg.gr3
            ln -sf ../vgrid.in.2d vgrid.bg
            ln -sf ../vgrid.in.3d vgrid.fg

         * Run script to create *uv3d.th.nc* in a conda environment with schimpy

         .. code-block:: console

            module purge
            module load schism/5.10_intel2022.1
            ulimit -s unlimited 
            interpolate_variables8

         * Copy the *uv3d.th.nc* file to the main folder

   #. Create symbolic links back in the main simulation folder

      .. code-block:: console

         ln -sf hotstart.20090501.nc hotstart.nc
         ln -sf SAL_nu_obsroms.nc SAL_nu.nc
         ln -sf TEM_nu_obsroms.nc TEM_nu.nc
         ln -sf salinity_nudge.gr3 SAL_nudge.gr3
         ln -sf temperature_nudge.gr3 TEM_nudge.gr3
         ln -sf param.nml.clinic param.nml
         ln -sf bctides.in.3d bctides.in
         ln -sf vgrid.in.3d vgrid.in
         ln -sf launch.clinic.pbs launch.pbs

   #. Run model for period which the internal salinity/temperature nudging runs (in this example, the model will stop after 7 days)

      .. code-block:: console

         qsub launch.pbs

   #. After model stops, need to restart from hotstart outputs from the previous run

      * Run combine_hotstart7 on last timestep output to hotstart within the outputs

      .. code-block:: console

         combine_hotstart7.exe --iteration 4800

      Note that the iteration variable is based on variables in param.nml *nhot_write* which is set to 4800 in this example. 4800 x *dt* = 4800 x 90s = 5 days

      * Change links to hotstart and nudging data

      .. code-block:: console

         ln -sf outputs/hotstart_it\=4800.nc hotstart.nc
         ln -sf SAL_nu_roms.nc SAL_nu.nc
         ln -sf TEM_nu_roms.nc TEM_nu.nc

      * Edit param.nml.clinic
         * Change ihot to *ihot = 2* to start outputs from the timestep in the new hotstart file

      * Run the model

      .. code-block:: console

         qsub launch.pbs


