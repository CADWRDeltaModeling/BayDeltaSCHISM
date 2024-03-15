
.. _hotstart:

=========================================
Run Initialization and Restart (Hotstart)
=========================================


When do you need an initial condition or hotstart?
--------------------------------------------------
You should use a hotstart or initialization for every study if you include salinity transport or other tracers.
The need for this may be unfamiliar if you are coming from a lower dimensional model or less
resolved 3D model. There are two reasons:

  * the domain is really big, so moving the salt in correctly via a cold start would take many months and 
  * if salinity is only coming in from the ocean a sharp baroclinic barrier shock will develop with possibly odd behavior. 

We mostly do barotropic runs (no salinity or transport) as a warmup to generate our ocean boundary. For
that a cold start from very basic (zero velocity, flat water elevation) is fine.

What is the difference between a cold and hot start?
-----------------------------------------------------

A cold start means values are initialized from very simple and well behaved values. Typically velocity is zero
and the water surface is flat. This avoids "mini-tsunamis".  Cold starts are invoked using `ihot=0` 
in the control file `param.nml`. You also need plausible values for initialization. 
If you our using our schism templates and requires some 
initial conditions be provided in the form of text \*.ic files which are like \*.gr3 files with values at each node, 
but don't have mesh topology in the file (and `param.nml.tropic` control file suggestions for a barotropic run) 
then a cold start is assumed and the text initialization file elev.ic (and any other *.ic file) will be built.

A hotstart means initializing a model with non-trivial values. There are two main cases:

ihot=1 (initial condition) 
    Start of run. In this case the hotstart file is compiled by the user using interpolated data. Often for this case
          the assumptions for elev and velocity are simplified and the details are supplied for tracers like temperature/salinity

ihot=2: (restart) 
    Restart of run. This is used in case you are transitioning to new conditions like study alternatives, 
    invoking a new set of modules or backing up and restart a failed run. In this case the hotstart file is
    generated using per-processor hotstart file in the outputs directory. 
          
Combining hotstarts
-------------------
In order to combine hotstarts for a restart you need to have the combine_hotstart utility on path. The actual name of the utility will be
something like `combine_hotstart7`, where the '7' part is a version that may evolve if the hotstart format changes.
The hotstart combining command is invoked in the outputs directory and requires specification of an iteration number:
`combine_hotstart7 -i 24000`. It will take the many per-processor files associated with the iteration 
(hotstart_000000_24000.nc, hotstart_000001_24000.nc, etc) and generate a single hotstart with a name like
`hotstart_it=24000.nc`. We prefer that you move this out of the outputs directory and rename it according to the following convention:
`hotstart.20210515.24000.nc`.

To do this you will need to know how to associate real dates with the iteration. Actually iteration is a possibly confusing term. 
The real interpretation is time step. So if the iteration is 24000, dt=90 seconds, then the time stamp of the hotstart is the start time 
of the run plus 24000*90 seconds. This is tedious, so if you have a `schimpy` installation on your machine, you can use the hotstart_inventory command line 
utility to get a list without doing all this calculation: `hotstart_inventory --dt=90 --start=2021-04-20`. 

The best translation of 'restart' in SCHISM is hotstart with ihot=2. 


.. _choose_runtime:
Choosing a good start time
--------------------------
By convention, our group chooses start times that coincide with USGS cruises. . Those are the days when you will have the best access 
to details on salinity and temperature in the Bay.  Note that many cruises are partial, involving only say 20 stops and covering perhaps only the
South Bay. You will want a date with a complete cruise. At the Delta Modeling Section we keep an inventory of these. 

Hotstart files are not trivially exchangeable when the grid changes or if you change modules (for instance, adding AGE midway through). 
However, if you have a hotstart from another grid or simulation, the schism_hotstart 
utility does have an option for initializing by interpolating from the prior hotstart onto the current mesh.

For model initialization, you will also need to consider your strategy for nudging. Nudging means the pushing of the model towards data, which
can tremendously speed up the initialization process and make it more accurate.  We use nudging
at all times at the ocean boundary for salt and temperature, essentially using it as a softer and wider boundary layer. 
We also sometimes use nudging based on observations in the Delta if we are doing an operational 
run with observed data and looking at the near term consequences of an action. Under these conditions, one usually wants the model to be spun
up fast and accurately. If we are doing longer term planning simulations or if there is branching into alternatives, nudging may not have a role.
Also labeling must be exceedingly clear. NEVER REPORT AS GENERAL MODEL ACCURACY STATISTICS ANY RESULTS USING MODELS THAT ARE ACTIVELY NUDGED INSIDE THE GOLDEN GATE.

The two pictures below show the common initialization sequences, as well as the extension into the main study period.

.. figure:: ../img/initialization1.png
   :class: with-border

   Simple initialization without nudging using Delta observations data.  * = Prefer USGS cruise date.

.. figure:: ../img/initialization2.png
   :class: with-border

   Simple initialization with nudging using Delta data to spin up the model fast and accurately, 
   before halting and restarting without nudging for the main study.




Creating a Hotstart for Hydro/Salt/Temp with schism_hotstart
------------------------------------------------------------




Acquiring the data
^^^^^^^^^^^^^^^^^^

It is hard to generalize all the different systems used by modeling groups to gather up observed data. 
The short answer is that for a hotstart you will need a USGS cruise file (downloading the whole year is fine, 
that is the way their interface looks at the time of writing). 


If you are using in-Delta observations you will also need QA/QC'd data at least for the instant of the hotstart.
Within the Delta Modeling Section, the script that does gathers these is `BayDeltaSCHISM/bdschism/bdschism/hotstart_nudging_data.py`. 
That script assumes a data repository full of observed data from multiple agencies that is not yet disseminated. If you need help, please contact us. 



Configuring the Hotstart request (yaml)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Running the hotstart generator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^




