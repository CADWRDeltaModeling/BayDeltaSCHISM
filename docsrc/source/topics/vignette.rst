
.. _bdschinstr:

Vignette: Details of a Simple Bay Delta SCHISM at Delta Modeling Section
========================================================================

The process for starting a Bay Delta SCHISM run from scratch involves some pre-processing work on a Windows machine using the schimpy library (https://github.com/CADWRDeltaModeling/schimpy).

You'll want to have a conda environment which has the latest version of schimpy in it. For this example that environment is called 'schism'.

Windows
******************************

#. Clone the Bay Delta Schism repository to your Windows machine (ex: D:/schism/bdsch_scratch)

   * git clone https://github.com/CADWRDeltaModeling/BayDeltaSCHISM.git (creates a BayDeltaSCHISM folder within bdsch_scratch)

#. Move some data

   * Copy the "./BayDeltaSCHISM/templates/bay_delta" folder into your base folder and rename (ex: baydeltainputs)
   * You'll need a .2dm file for the pre-processor, copy this into the baydeltainputs folder
   * Copy "./BayDeltaSCHISM/data/time_history/\*.th" files into baydeltainputs folder
   * Copy "./BayDeltaSCHISM/data/flow_station_xsects.yaml" into baydeltainputs folder


#. Edit input files

   * main_bay_delta.yaml
      * change mesh_inputfile: parameter to match the .2dm file you copied into the project folder
      * check that the vgrid: section contains a vgrid_version: variable set to the SCHISM version being used (5.8 or 5.10)
   * dem_4.2_cc.yaml
      * check the Dutch Slough DEM location, if unknown then comment output
   * sav_density.yaml
      * change "W:/sav" to "//nasbdo/Modeling_Data/sav" for all cases where "W:/sav" is found

#. Run pre-processor

   * in a conda terminal run:

   .. code-block:: console
    
       conda activate schimpy
       prepare_schism main_bay_delta

#. Create Hotstart and Nudging datasets

   * This can be done in a seperate folder from the repository cloned, and seperate from the model inputs, since you only need a few of the resulting files to copy into the final model folder. (ex: bdsch_scratch/model_hotstart/)

   * Hotstart and Nudging input datasets:

      * Use hotstart_nudging_data.py to create the \*.csv files necessary for the next step which creates the \*.nc files which SCHISM uses

         .. warning::

            In order to use this utility you'll need to have dms_datastore in your environment. I created a schism-dms environment which uses *this environment.yml file LINK*

        * You'll need to specify the length of time you're nudging the data (ex: 7 days)
        
        .. code-block:: python

           nudgelen = days(7)
        
        * Also specify the start date that the model will run from (es: May 1, 2009)
        
        .. code-block:: python

           t0 = pd.Timestamp(2009,5,1)

        * Run hotstart_nudging_data.py in your 'model_hotstart' folder to produce 'hotstart_data_temperature.csv', 'hotstart_data_salinity.csv', 'nudging_data_temperature.csv', 'nudging_data_salinity.csv'

      * Download polars .csv data `here`_

         * go to the year of your start date, select "All" from the drop-down, export csv and save to "model_hotstart\USGS\_{year}_saltemp.csv" 
      
      .. _here: https://sfbay.wr.usgs.gov/water-quality-database/

      * Review and QA/QC the downloaded data from the above two steps
         
         * this step looks for negative temperatures/salinity and evaluates the data for any spikes or other anamolies
         * SCRIPT HERE

   * Creating Hotstart and Nudging \*.nc Model inputs

   This step relies on the schimpy package and uses two files (hotstart.yaml and nudging.yaml) along with a script "hotstart.py"

      * hotstart.yaml
         
         * for all data using 'extrude_casts:' replace 'data:' entry with the polaris csv file "USGS\_{year}_saltemp.csv"
         * for all data using 'obs_points:' replace 'data:' entry with "hotstart\_data\_{salinity/temperature}.csv" depending on the 'variable:'
         * set 'vgrid_version:' to 5.8 *NOTE: this will be updated in schism_hotstart and schism_nudging so that you can put in the real vgrid_version*

      * nudging.yaml

         * set 'vgrid_version:' to 5.8 *NOTE: this will be updated in schism_hotstart and schism_nudging so that you can put in the real vgrid_version*
         * change the run days based on your previous number (ex: 7 days)

           .. code-block:: text

              rnday: 7

         * change temperature and salinity 'data:' to point to "nudging\_data\_{temperature/salinity}.csv"
           
   * This should have created hotstart.nc, SAL_nu_obsroms.nc, SAL_nu_roms.nc, TEM_nu_obsroms.nc, and TEM_nu_roms.nc so copy these files into the model inputs folder "baydeltainputs"

      * rename the hotstart.nc file to something relevant like "hotstart.20090501.nc" or whatever your start date is

Linux
******************************
        
#. Create the folder where you will be running the model (ex: /scratch/dms/{username}/schism/bdsch_scratch_demo)

   * from your Windows machine, copy "D:/schism/bdsch_scratch/BayDeltaSCHISM/templates/bay_delta/make_links.py" into your Linux model folder (bdsch_scratch_demo) 
   * in the model folder run these commands:

   .. code-block:: console

    mkdir sflux
    cd sflux
    python make_links.py
    cd ..

   * copy the contents of your Windows model inputs folder (baydeltainputs) into the Linux model folder (bdsch_scratch_demo)

   * link the following files:

   .. code-block:: console

    ln -s bctides.in.3d bctides.in
    ln -s param.nml.clinic param.nml
    ln -s hotstart.20090501.nc hotstart.nc
    