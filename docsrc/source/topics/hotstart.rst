

=========================================
Run Initialization and Restart (Hotstart)
=========================================


When do you need an initial condition or hotstart?
--------------------------------------------------
You should use a hotstart or initialization for every study if you include salinity transport.
This may be unfamiliar if you are coming from a lower dimensional model or less
resolved 3D model. There are two reasons we do this 1) the domain is really big, so moving
the salt in correctly via a cold start would take forever and 2) if salinity is only coming in
from the ocean a sharp baroclinic barrier shock will develop with possibly odd behavior. 

We mostly do barotropic runs (no salinity or transport) as a warmup to generate our ocean boundary. For
that a cold start from very basic (zero velocity, flat water elevation) is fine.

What is the difference between a cold and hot start
-----------------------------------------------------

A cold start means values are initialized from very simple and well behaved values, typically velocity is zero
and the water surface is flat. This avoids "mini-tsunamis".  Cold starts are invoked using `ihot=0` in the control file `param.nml`. 
You also need plausible values for initialization. If you our using our schism templates and requires some 
initial conditions be provided in the form of text *.ic files which are like *.gr3 files with values at each node, 
but don't have mesh topology in the file (and param.nml.tropic control file suggestions for a barotropic run) 
then a cold start is assumed and the text initialization file elev.ic (and any other *.ic file) will be built.

A hotstart means initializing a model with non-trivial values. There are two main cases:

  ihot=1: Start of run. In this case the hotstart file is compiled by the user using interpolated data. Often for this case
          the assumptions for elev and velocity are simplified and the details are supplied for tracers like temperature/salinity
  ihot=2: Restart of run. This is used in case you are transitioning to new conditions like study alternatives, 
          invoking a new set of modules or backing up and restart a failed run. In this case the hotstart file is
          generated using per-processor hotstart file in the outputs directory. 
          
Combining hotstarts
-------------------
In order to combine hotstarts you need to have the combine_hotstart utility on path. The actual name of the utility will be
something like `combine_hotstart7` and the command requires specification of an iteration number:
`combine_hotstart7 -i 24000`. Use the most recent version available from your build and invoke it in your outputs
directory. It will take the many per-processor files associated with the iteration 
(hotstart_000000_24000.nc, hotstart_000001_24000.nc, etc) and generate a single hotstart with a name like
`hotstart_it=24000.nc`. We prefer that you move this out of the outputs directory and rename it according to the following convention:
`hotstart.20210515.24000.nc`.

To do this you will need to calculate the iteration which is a possibly confusing term. 
Iteration in this one case means time step. So if the iteration is 24000 and dt=90 seconds, then the iteration is the start time 
of the run plus 24000*90 seconds. If you have a `schimpy` installation on your machine, you can use the hotstart_inventory command line 
utility to get a list without doing all this calculation: `hotstart_inventory --dt=90 --start=2021-04-20`. 

Restart is a name used in some modeling systems. The best translation in SCHISM is hotstart with ihot=2. 


Choosing a good start time
--------------------------
The easiest start times in SCHISM are associated with USGS cruise dates, because on those dates you 
have pretty good details on salinity in the Bay. USGS cruises are available here: **. Note that many cruises are partial.
You will want a complete cruise. At the Delta Modeling Section we keep an inventory of this. 

You will also need to consider your strategy for nudging. Nudging means the pushing of the model towards data, which
can tremendously speed up the initialization process and make it more accurate.  Nudging is covered here**. We use nudging
at all times at the ocean boundary to reconcile near-boundary values with results of coastal models, where it both softens and 
enhances the imposition of coastal boundary conditions. We sometimes use nudging to internal data if we are doing an operational 
run with observed data and looking at the near term consequences of an action. If we are doing longer term planning or branching into
alternatives, nudging may not have a role.

The two pictures below show the common initialization sequences, as well as the extension into the main study period.

.. figure:: ../img/initialization1.png
   :class: with-border

   Simple initialization without nudging using Delta data.

.. figure:: ../img/initialization2.png
   :class: with-border

   Simple initialization with nudging using Delta data to spin up the model fast and accurately, 
   before halting and restarting without nudging for the main study.









Creating a Hotstart for Hydro/Salt/Temp
---------------------------------------

Just checking
^^^^^^^^^^^^^