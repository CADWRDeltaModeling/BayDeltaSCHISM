
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


Prepping the data
-----------------

Sequencing your run
-------------------
.. mermaid::
    :name: nudge_flow

    graph LR
      hgrid[hgrid.gr3] --> nudge_py[Run: nudging.py];
      vgrid3["vgrid.in.3d"] --> nudge_py;
      nudge(["Start: nudging input"]) --> nudge_ts["Nudging time series in .csv"] --> nudge_py;
      nudge_py --> nudge_nc["{MOD}_nu.nc & {MOD_nudge.gr3}"];
      hycom_input["hycom_input"] --> nudge_py;
      nudge_nc --> baroclinic{"Baroclinic Simulation"};
