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
===================

In BayDeltaSCHISM/data we provide flux.th, salinity.th (maps to SAL_1.th) and temperature.th (maps to TEM_1.th) that go back to roughly
2008. Before that, operations were different and some of our better data sources were unavailable.


Clipping to run dates and conversion to elapsed time
====================================================

The .th format uses elapsed seconds from run start for time and has no headers. Our data are provided in what we call dated format. We mix it down before
the run.


What if I have to add or move a boundary?
==========================================

Moving the grid relative to the boundary or a boundary relative to the grid has consequences in some far flung places. 
You'll want to cover our :ref:`checklist <change_mesh>` of consequences and consider which apply to your case.

Please also note that our boundary condition file is constructed, in order, from our most common boundaries. If you add a boundary you may have to
inject a column into the flux.th file.

.. _the examples folder: https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/port_boundary

.. _port_boundary:

Porting Boundaries from Other Sources
========================================

The :file:`port_boundary.py` script in BayDeltaSCHISM/bdschism/bdschism/  contains utilities 
to convert or graft outputs from various data formats (other models or forecasts) onto 
files in SCHISM time history (.th) formats. There are a few examples of how to use this utility in `the examples folder <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/port_boundary>`_. 
You can find an example to take outputs `from CalSim DSS <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/port_boundary/from_CalSim>`_, `from CSV files <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/port_boundary/from_csv>`_, and `from monthly CSV files <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/port_boundary/from_monthly_csv>` and convert them to SCHISM inputs. All of the example data are available within the folders so you can see what gets exported based on the examples.

**File Descriptions**
----------------------

  :file:`port_boundary.py`: main script

  :file:`port_boundary.yaml`: configuration file 

  :file:`port_boundary_map.csv`: configuration mapping file 


.. currentmodule:: port_boundary
.. autofunction:: port_boundary.port_boundary_cli

.. _port_boundary_yaml:

**Configuring the port_boundary yaml file**
-----------------------------------------------

You can see sample yamls in `the examples folder`_, but here is an overview of the yaml options:

config
```````
All items in the **config** section can be used as variables throughout this yaml as well as the in the source_map_file (`port_boundary_map`)

.. code-block:: yaml

    config:
        project_dir: ./ # useful but not necessary. If it's relevant to your project, could be handy
        version: bdschism_demo # useful but not necessary. If it's relevant to your project, could be handy
        out_dir: ${project_dir}/${version}/ # where the schism input files will be stored to from port_boundary
        bds_home: ../../../ # where to find the BayDeltaSCHISM folder
        calsim_dss: ${project_dir}/calsim_output_example.dss # used in the cu section below as well as in the source_map_file

param
```````
determine which kinds of boundaries will be ported, all must be represented in the source_map_file

.. code-block:: yaml

    param:
        boundary_kinds: [flow,delta_cross_channel,montezuma_boat_lock,montezuma_flash,montezuma_radial,cu] #[flow,delta_cross_channel,montezuma_boat_lock,montezuma_flash,montezuma_radial,cu,salt,temp]
        overwrite: true # if true, overwrite the existing boundary inputs (should be false for forecast)
        start_date: 2022,1,1 #YYYY,MM,DD - but can be filled using --sd flags (see example at bottom)
        end_date: 2023,12,31 #YYYY,MM,DD - but can be filled using --sd flags (see example at bottom)

file
```````
show which files will be used for headers etc as well as what the suffix of the output files will be

.. code-block:: yaml

    file:
    source_map_file: ./port_boundary_map_calsim_schism.csv # ESSENTIAL. This is what determines where the boundaries' sources are as well as any interpolation or math will be performed on them
    schism_flux_file: ${bds_home}/data/time_history/flux.th # the basis for the flux timeseries, any un-listed columns in source_map_file will be kept as the original column in the flux.th file.
    schism_salt_file: ${bds_home}/data/time_history/salt.th # the basis for the salt timeseries
    schism_temp_file: ${bds_home}/data/time_history/temp.th # the basis for the temperature timeseries
    schism_gate_dir: ${bds_home}/data/time_history # where to find any gate files
    out_file_suffix: ${version}.dated # the suffix of the final SCHISM input .th files

cu (optional)
```````````````
Consumptive use specifications are shown here. This section is only useful if you are porting consumptive use to SCHISM. When this part of the ymal is used, you can use parse_cu independently with this yaml file. See :ref:`Parsing Consumptive Use <parse_cu>` for more details.


Use
----

.. code-block:: console

  bds port_bc port_calsim_schism.yaml -- --sd 2015/2/18 --ed 2016/5/15

.. _port_boundary_map:

**Configuring the mapping file**
-----------------------------------

The mapping file :file:`port_boundary_map.csv` is the main configuration file in which the SCHISM variables are mapped to their respective substitution variables and sources.
The mapping file can use ${} classifiers to set values with either a command line-type variable dictionary or by using values set in the yaml file's config section.

  1. **schism_boundary**: the SCHISM boundary variable

  2. **boundary_kind**: type of boundary (flow, ec, temp)

  3. **source_kind**: the type of file to convert from (SCHISM, CSV, DSS, CONSTANT)


    .. note::  If SCHISM is used as the source, values from the designated SCHISM .th file are copied over and used directly.

    .. note::  for CSV *source_kind*: pd.read_csv() is used to parse the csv and, as coded, parses data. The format of a csv source_kind is shown in the table below. The column is specified in the "var" column of the mapping csv.

                +------------+-----------+----------+----------+
                | date       | RSAC155   | RSAN112  | var_n    |
                +============+===========+==========+==========+
                | 1/1/2014   | 5609      | 1233     | ...      |
                +------------+-----------+----------+----------+
                | 1/2/2014   | 4771      | 1162     | ...      |
                +------------+-----------+----------+----------+
                | ...        | ...       | ...      | ...      |
                +------------+-----------+----------+----------+

    .. note::  for DSS *source_kind*, CalSim or DSM2 standard DSS files may be used. The pathname is specified in the "var" column of the mapping csv.

    .. note:: for CONSTANT *source kind*, input a value in the 'var' column. This may be used when an input boundary is generlly constant (.e.g, Sacramento River boundary EC).

  4. **derived**: whether to use the variable directly, or calculate based on other variables. For example SCHISM variable 'east' is sum of DSM2 variables RCSM075 and RMKL070.

  .. note:: if derived is TRUE, then you need to specify the formula in the "formula" column of the mapping csv.

  5. **source_file**: path of the source_file (relative path)

  6. **var**: variable name within the source file. For DSS this is a pathname, for csv this is the header(s) used for this boundary.

  7. **sign**: multiplied by timeseries to change direction of flow.
  
  8. **convert**: apply unit conversions (CFS_CMS, EC_PSU)::

        if convert == 'CFS_CMS':
            dfi = dfi * CFS2CMS * sign
        elif convert == 'EC_PSU':
            dfi = ec_psu_25c(dfi) * sign

  9. **rhistinterp_p**: this script uses `rhistinterp <https://github.com/CADWRDeltaModeling/vtools3/blob/b7cfa54f45e8efa803cb3ebfb4f580d1e9719957/vtools/functions/interpolate.py#L15>`_ to interpolate and smooth timeseries of coarser timesteps.
      This field sets the parameter p. For smoothing which maintains a decent fidelity to the total volume/flow use a value of 2. If you want less splining and are worried about the interpolation overshooting a threshold (like zero) then use a higher value of 8+.

  10. **formula**: the formula for the derived timeseries Used if derived = TRUE.

    .. note::  Python's eval() function is used to parse the code entered in the cell.
      Examples::

        (csv.RCSM075+csv.RMKL070)

      The above entry would sum up RCSM075 and RMKL070 from the CSV source ::

        (flux.american/(flux.sac+flux.american)).mul(csv.RSAC155)
      
      The above entry would multiply the RSAC155 from the CSV source by the ratio of the (Amer River/Amer+Sac River). This is used to disaggregate the total Sacramento R. flow above the confluence (i.e., from DSM2) into its American River component, based on an existing SCHISM flux.th input.

        np.minimum(3000, dss.C_CSL004A)

      The above entry would set the value to the minimum of 3000 or the data in the dss file using the B part C_CSL004A. This is used in the Yolo Toedrain where you want a maximum value of 3000 cfs in the channel.
      
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

  11. **note**: This is simply a space to notate the intention of the boundary. This is purely for human-readable content and clarity on future use.

.. _parse_cu:

Parsing Consumptive Use
=========================

In the bdschism package, there is a utility called parse_cu that can be used to convert consumptive use data from various source files into SCHISM vsource.th and vsink.th files. 
This utility can be run independently or as part of the port_boundary script when the 'cu' section is included in the port_boundary yaml file.


.. currentmodule:: parse_cu
.. autofunction:: parse_cu.parse_cu_yaml_cli

Configuring the parse_cu yaml file
-----------------------------------

.. code-block:: yaml
    
    cu:
    process: orig_pert_to_schism # net_diff_to_schism or orig_pert_to_schism
    original_type: dsm2 # dsm2, calsim, obs_schism, csv
    original_filename: ${project_dir}/dsm2_dcd_example.dss # parse_cu will look to this consumptive use as the basis
    perturbed_type: calsim # dsm2, calsim, obs_schism, csv
    perturbed_filename: ${calsim_dss} # parse_cu will look to this consumptive use to difference against the original 
    schism_vsource: ${bds_home}/data/channel_depletion/vsource_dated.th # used for the locations and headers to use for vsource
    schism_vsink: ${bds_home}/data/channel_depletion/vsink_dated.th # used for the locations and headers to use for vsource
    out_dir: ${out_dir} # where the consumptive use files will be written (useful if not running full port_boundary)
    version: ${version} # used in naming the output th files (e.g. vsource.bdschism_demo.dated.th)
    start_date: ${sd} #YYYY,MM,DD - but can be filled using --sd flags (see example at bottom)
    end_date: ${ed} #YYYY,MM,DD - but can be filled using --sd flags (see example at bottom)
    

Plotting Input Boundaries
==========================

In order to plot the boundaries you have created or ported, you can use the bds plot_bds_bc utility.


.. currentmodule:: plot_input_boundaries
.. autofunction:: plot_input_boundaries.plot_bds_bc_cli

Use
----

To plot the boundaries, go to out_dir and run:

.. code-block:: console

  bds plot_bds_bc -o --sim-dirs ./ --html-name bds_input_boundaries.html -- --flux_file flux.dated.th --vsource_file vsource.dated.th --vsink_file vsink.dated.th