
.. _nudging:

=============
Nudging Files
=============

Introduction: What is nudging?
------------------------------


.. _nudge_obs_grid:

.. figure:: ../img/nudging_obs_gr3.png
   :class: with-border
   :width: 70%
   :align: center
   
   Nudging relaxation shown around EC and temperature stations. Red shows where the nudging is applied the greatest, Blue is the least, and White induces no nudging. The relaxation constants are specified in the [MOD]_nudge.gr3 file. The locations and values are specified in the \*.yaml files.

.. _nudge_ocean_grid:

.. figure:: ../img/nudging_ocean_gr3.png
   :class: with-border
   :width: 70%
   :align: center
   
   Nudging relaxation shown along the ocean boundary. Similar color scale to Fig. :numref:`nudge_obs_grid`. Also the stations used to interpolate along the ocean boundary are specified in the \*.yaml files.

In SCHISM you can use a NetCDF file that coerces/nudges module values towards an observed or set timeseries in specific points throughout the model.
You can see the param.nml settings in the nudging block::

    inu_tr(1) = 2 !T
    inu_tr(2) = 2 !S
    inu_tr(3) = 0 !GEN
    inu_tr(4) = 0 !Age
    inu_tr(5) = 0 !SED3D
    inu_tr(6) = 0 !EcoSim
    inu_tr(7) = 0 !ICM
    inu_tr(8) = 0 !CoSINE
    inu_tr(9) = 0 !FIB
    inu_tr(10) = 0 !TIMOR
    inu_tr(11) = 0 !FABM

    vnh1 = 400 !vertical nudging depth 1
    vnf1 = 0. !vertical relax \in [0,1]
    vnh2 = 500 !vertical nudging depth 2 (must >vnh1)
    vnf2 = 0. !vertical relax

    step_nu_tr = 3600. !time step [sec] in all [MOD]_nu.nc (for inu_[MOD]=2)

Where inu_tr(N) is set to 2 if a NetCDF file is used to nudge values for that module, and set to 0 if no nudging is used. For instance temperature (N=1) or salinity (N=2) are most often set to 2, and require `[MOD]_nu.nc`` as well as `[MOD]_nudge.gr3`` as inputs. The .nc file specifies the values to be nudged to, and the .gr3 file specifies the horizontal relaxation constants, which are applied with the vertical nudging relaxation specified by a linear function of `vnh[1,2]` and `vnf[1,2]`. We typically use one hour nudging (3600) which is needed if using data with relatively fast nudging rates.

Do I need nudging?
------------------
Nudging is used for two things:
1. Soft coastal boundary enforcement
2. Initialization: fast spin-up over brief period using observations over the whole domain

It is common for a single simulation to start and finish with different nudging products. Typically, the first nuding is dense, utilizing data from many observation stations, and is used to spin up the model quickly. The second is intended to only provide coastal data.

Generating nudging files
-----------------
The python function to generate nudging files is `create_nudging`, which is part of [schimpy](https://github.com/CADWRDeltaModeling/schimpy/blob/master/schimpy/nudging.py). The function is run as follows:

`create_nudging --input config_file`

 Here, `config_file` is in yaml format, examples of which can be found on the [BayDeltaSCHISM](https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/nudging)

### Preparing for nudging with observation data

For nudging using observtion data, one must prepare the time series inputs using `hotstart_nudging_data` from [BayDeltaSCHISM](https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/bdschism/bdschism/hotstart_nudging_data.py).

The start date, length of nudging, and the location of the time series files need to be specified in the following manner:
`python hotstart_nudging_data.py --start_date 2021-01-01 --nudge_len 10 --repo_dir $repo`, where `$repo` is the path to raw observation data.

The recommended spin-up period using observation data is 10-15 days.

Sequencing your run
-------------------
.. raw:: html 
    :file: ../img/nuding_flowchart.svg

.. this is from the following code:
.. ---
.. config:
..   look: classic
..   theme: redux
..   layout: elk
.. ---
.. flowchart LR
..     hgrid["Horizontal Grid: 
..             hgrid.gr3"] --> nudge_py["Run: nudging.py"]
..     vgrid3["Vertical Grid:
..             vgrid.in.3d"] --> nudge_py
..     nudge(["Start: nudging input"]) --> nudge_ts["Nudging time series 
..                         in .csv"]
..     nudge_ts --> nudge_py
..     nudge_py --> nudge_nc["{MOD}_nu.nc & {MOD_nudge.gr3}"]
..     hycom_input["hycom_input"] --> nudge_py
..     nudge_nc --> baroclinic{"Baroclinic Simulation"}
..     hgrid@{ shape: doc}
..     vgrid3@{ shape: doc}
..     nudge_ts@{ shape: docs}
..     nudge_nc@{ shape: docs}
..     style baroclinic fill:#BBDEFB
..     click hgrid "https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/topics/mesh.html#"
