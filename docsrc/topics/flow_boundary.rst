


#########################
Inflow/Outflow Boundaries
#########################

Inflow/outflow boundaries locations specified in `hgrid.gr3`, usually with the preprocessor identifying the start 
and end of the string of nodes. The fact that a boundary is a flow or tracer
boundaries is specified in `bctides.in`. The actual data are provided in `flux.th` for flow
and `SAL_1.th`, `TEM_1.th` for other tracers. For info on the .th file format, 
you can refer to the `SCHISM manual <https://schism-dev.github.io/schism/master/input-output/optional-inputs.html#th-ascii>`_
on the topic.


Where are the data?
##################

In BayDeltaSCHISM/data we provide flux.th, salinity.th (maps to SAL_1.th) and temperature.th (maps to TEM_1.th) that go back to roughly
2008. Before that, operations were different and some of our better data sources were unavailable.


Clipping to run dates and conversion to elapsed time
####################################################

The .th format uses elapsed seconds from run start for time and has no headers. Our data are provided in what we call dated format. We mix it down before
the run.


What if I have to add or move a boundary?
#########################################

Moving the grid relative to the boundary or a boundary relative to the grid has consequences in some far flung places. 
You'll want to cover our :ref:`checklist <change_mesh>` of consequences and consider which apply to your case.

Please also note that our boundary condition file is constructed, in order, from our most common boundaries. If you add a boundary you may have to
inject a column into the flux.th file.


Adding Data From Other Sources (e.g. Forecasts, other models)
#############################################################


The :file:`port_boundary.py` script in BayDeltaSCHISM/scripts/  contains utilities 
to convert or graft outputs from various data formats (other models or forecasts) onto 
files in SCHISM time history (.th) formats. 

.. currentmodule:: port_boundary
.. autofunction:: read_csv


  **File Descriptions**

    :file:`port_boundary.py`: main script
  
    :file:`port_boundary_map.csv`: configuration file 
  
  **Configuring the mapping file**

  The mapping file :file:`port_boundary_map.csv` is the main configuration
  file in which the SCHISM variables are mapped to their respective substitution variables and sources.
  
    1. **schism_boundary**: the SCHISM boundary variable
  
    2. **boundary_kind**: type of boundary (flow, ec, temp)
  
    3. **source_kind**: the type of file to convert from (SCHISM, CSV, DSS, CONSTANT)
  
  
      .. note::  If SCHISM is used as the source, values from the designated SCHISM .th file are
       copied over and used directly.
  
      .. note::  for CSV *source_kind*: pd.read_csv() is used to parse the csv and, as coded, parses
                 monthly data. The format of a csv source_kind is shown in the table below.
  
                 +------------+-----------+----------+----------+
                 | date       | RSAC155   | RSAN112  | var_n    |
                 +============+===========+==========+==========+
                 | 1/1/2014   | 5609      | 1233     | ...      |
                 +------------+-----------+----------+----------+
                 | 1/2/2014   | 4771      | 1162     | ...      |
                 +------------+-----------+----------+----------+
                 | ...        | ...       | ...      | ...      |
                 +------------+-----------+----------+----------+
  
      .. note::  for DSS *source_kind*, CalSim or DSM2 standard DSS files may be used.
  
      .. note:: for CONSTANT *source kind*, input a value in the 'var' column. This may be used when an input boundary is
         generlly constant (.e.g, Sacramento River boundary EC).
  
    4. **derived**: whether to use the variable directly, or calculate based on other variables. For example SCHISM variable 'east' is sum of DSM2 variables RCSM075 and RMKL070.
  
    5. **source_file**: path of the source_file (relative path)
  
    6. **var**: variable name within the source file.
  
    7. **sign**: multiplied by timeseries to change direction of flow.
    
    8. **convert**: apply unit conversions (CFS_CMS, EC_PSU)::

         if convert == 'CFS_CMS':
            dfi = dfi*CFS2CMS*sign
         elif convert == 'EC_PSU':
            dfi = ec_psu_25c(dfi)*sign

    9. **rhistinterp_p**: this script uses `rhistinterp <https://github.com/CADWRDeltaModeling/vtools3/blob/b7cfa54f45e8efa803cb3ebfb4f580d1e9719957/vtools/functions/interpolate.py#L15>`_ to interpolate and smooth timeseries of coarser timesteps.
       This field sets the parameter p
  
    10. **formula**: the formula for the derived timeseries Used if derived = TRUE.

      .. note::  Python's eval() function is used to parse the code entered in the cell.
                 Examples::
                   (csv.RCSM075+csv.RMKL070)
                 The above entry would sum up RCSM075 and RMKL070 from the CSV source
                 ::
                 
                   (flux.american/(flux.sac+flux.american)).mul(csv.RSAC155)
                 The above entry would multiply the RSAC155 from the CSV source by the ratio of the (Amer River/Amer+Sac River).
                 This is used to disaggegate the total Sacramento R. flow above the confluence (i.e., from DSM2) into its American
                 River component, based on an existing SCHISM flux.th input.
                 
                 **The dataframes are named:**
                 
                     *flux*: DataFrame containing the historical SCHISM flux.th file
                     
                     *salt*: DataFrame containing the historical SCHISM salt.th file
                     
                     *temp*: DataFrame containing the historical SCHISM temp.th file
                     
                     *csv*: DataFrame containing the values from the CSV source
                     
                     *dss*: DataFrame containing the values from the DSS source
                 
      .. note::  the SCHISM time history files used are the ones in this repository.
                 ::
                 
                   schism_flux_file = '../data/time_history/flux.th'
                   schism_salt_file = '../data/time_history/salt.th'
                   schism_temp_file = '../data/time_history/temp.th'