
.. _barotropic:

###############################################
Ocean Boundary Stabilization: Barotropic Warmup
###############################################

Introduction
============

This section describes some issues with the a common practice with Bay-Delta SCHISM: a barotropic warmup run. 

The idea and potential need for a barotropic warm up harks to the well-posedness of the hydrostatic, layered 3D-equations,
the mainstay of estuarine circulation models. The pertinent reference is :cite:p:`oliger_theoretical_1978`. 
The idea is that we are allowed one boundary condition per "incoming characteristic". For transport of tracers (salinity, temperature, etc) this is the same as one boundary condition per incoming flow. 
This has a very intuitive feel -- we can only specify concentrations for flows
directed into the computational domain. For baroclinic hydrodynamics using layered equations, the number of
boundary conditions is potentially infinite, time varying, and discretization dependent. 

The upshot is that we have two choices for the ocean boundary. We can choose to clamp only water levels, 
which is underspecified and potentially allows baroclinic modes to "flare up" (:numref:`flareup`) if the model is not diffusive enough. Or we can specifiy velocity, which is in general overdetermined, and this potentially stabilizes the boundary. 

There are two methods of specifying velocity that have been used with the Bay-Delta SCHISM model:

  * force the model using estimates from a coastal open model such as the West Coast Forecasting System. 
  * do a preliminary 2D barotropic run and harvest boundary values from that. 

The coastal model solution makes sense in some operational scenarios, which focus on recent and observable scenarios. The barotropic-baroclinic solution is widely used in Bay-Delta SCHISM, as it applies to hypothetical hydrologies landscape change
and sea level rise.

.. _flareup:

.. figure:: ../img/ocean_flareup.png
   :class: with-border
   
   Velocity flareup right near boundary due to stimulation of baroclinic modes.


Set up
======

bctides.in
^^^^^^^^^^

param.nml
^^^^^^^^^

vgrid.in
^^^^^^^^




Run interpolate_variables to get uv3D.th.nc
-------------------------------------------

Move the outputs directory aside
--------------------------------



