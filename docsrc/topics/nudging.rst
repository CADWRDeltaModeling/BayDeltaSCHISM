
.. _nudging:

=============
Nudging Files
=============

Introduction: What is nudging?
------------------------------



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
