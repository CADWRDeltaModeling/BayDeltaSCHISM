
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

A cold start means values are initialized from very simple and well-behaved values. Typically velocity is zero
and the water surface is flat. This avoids "mini-tsunamis" that develop if we try to get too clever
with the initial water surface profile.  Cold starts are invoked using `ihot=0` 
in the control file `param.nml`. You also need plausible values for initialization. 
The SCHISM templates may require initial conditions in text ``*.ic`` files,
which are like ``*.gr3`` files with values at each node but no mesh topology.
For the barotropic configuration suggested by ``param.nml.tropic``, the
preprocessor builds ``elev.ic`` and any other configured ``*.ic`` files.

A hotstart means initializing a model with non-trivial values. There are two main cases:

ihot=1 (initial condition) 
    Start of run. In this case the hotstart file is compiled by the user using interpolated data. Often for this case the assumptions for elev and velocity are simple and the details are supplied 
	only for tracers like temperature/salinity

ihot=2: (restart) 
    Restart of run. This is used in case you are transitioning to new conditions (say, at the
	branching point where study alternatives diverge), invoking a new set of modules or 
	backing up and restarting a failed run. In this case the hotstart file is generated 
	by checkpoint hotstarts written out at regular intervals (often we choose one per five days).
	These are fragmented files, one per-processor, and need to be combined 
	using the `combine_hotstart` utility. This utility and a utility hotstart_inventory are described below. 
          

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

``schimpy.schism_hotstart`` creates an initial-condition hotstart or transfers a
prior hotstart onto a target grid. Put the complete configuration in YAML and
run it directly::

    create_hotstart hotstart.yaml

The grouped schimpy command is equivalent::

    sch create_hotstart hotstart.yaml

Do not add a ``create_hotstart.py`` driver for new work. Some older examples
still contain one because modules and other arguments used to be supplied from
Python. Current configurations should declare those inputs in YAML.

The ``hotstart`` block must identify the target grid, vertical grid and model
clock. For ``ihot=1``, ``run_start: default`` sets the time origin to ``date``.
For an ``ihot=2`` continuation, ``run_start`` remains the original simulation
origin and ``date`` is the restart moment. Schimpy computes ``time``, ``iths``
and ``nsteps_from_cold`` from those values and ``time_step``; do not patch the
clock variables after creating the file.

Each requested variable has one initializer. Common choices are:

``simple_trend``
    A constant or an expression in ``x``, ``y`` and depth ``z``.

``extrude_casts``
    Vertical cruise or profile observations, normally used in the Bay and
    estuary.

``obs_points``
    Station observations, normally used where the Delta or marsh network is
    dense.

``text_init``
    A field such as a generated ``elev.ic``.

``hotstart_nc``
    A prior hotstart, optionally with source horizontal and vertical grids for
    transfer to a changed mesh.

``patch_init``
    Dispatches different initializers by region. Region sources may be a
    shapefile or a schimpy polygon YAML file.

When elevation uses ``hotstart_nc``, set ``max_blw_bed`` inside that initializer.
It is a non-negative limit on how far the initialized surface at a novel target
node may sit below the target bed. It is not a tracer setting and does not belong
at the top level::

    elevation:
      initializer:
        hotstart_nc:
          data_source: source_hotstart.nc
          source_hgrid: source_hgrid.gr3
          source_vgrid: source_vgrid.in.3d
          source_vgrid_version: "5.10"
          max_blw_bed: 0.01

Wet/dry handling depends on whether elevation came from a prior hotstart. At
target nodes that coincide with source nodes, an elevation ``hotstart_nc``
retains the source ``idry`` flag. Nodes without a matched source flag, and nodes
initialized by other methods, are evaluated on the target grid: a node is dry
when ``dp + eta <= h0``. Side and element flags are then derived from the
completed target-node flags.

Examples
^^^^^^^^

Applied configurations are under ``examples/hotstart/`` in BayDeltaSCHISM.
They illustrate constants, cruise casts, station observations, changed-grid
transfer, flooded islands, sediment, age and biology modules. They are reference
configurations rather than self-contained test cases: shared target grids,
vertical grids and source hotstarts are not distributed. Several module cases
also retain legacy Python drivers or YAML that predates current required keys.
Use them to choose initializer patterns, then check configuration keys against
the current schimpy documentation and CLI.



Acquiring the data
^^^^^^^^^^^^^^^^^^

It is hard to generalize all the different systems used by modeling groups to gather up observed data. 
The short answer is that for a hotstart you will need a USGS cruise file (downloading the whole year is fine, 
that is the way their interface looks at the time of writing). 


If you are using in-Delta observations you will also need QA/QC'd data at least for the instant of the hotstart.
Within the Delta Modeling Section, the script that does gathers these is `BayDeltaSCHISM/bdschism/bdschism/hotstart_nudging_data.py`. 
That script assumes a data repository full of observed data from multiple agencies that is not yet disseminated. If you need help, please contact us. 

Initializing Restoration Areas and Gradual Inundation
------------------------------------------------------

When a restoration action adds wettable terrain, a prior hotstart does not by
itself define the new area's initial state. Decide whether the area should start
dry, at a designed pool level, or continuous with the adjacent channel, and
whether it is isolated by a hydraulic structure at the restart time. This is a
modeling decision, not something to infer from the old restart.

Use ``schimpy.inundate_island`` when a restored island is held behind temporary
hydraulic structures and opened gradually. Start from the finished base grid and
write a restoration specification containing each island polygon, breach
geometry, dredge depths, structure and optional breach date. See the
:external+schimpy:ref:`schimpy hydraulic-structures reference
<hydraulic_structures>` for structure types, mesh setup and general
operating-data guidance. The workflow here adds the initial-state and
changed-grid requirements specific to inundation.

Generate the coupled inputs with::

        sch inundate_island \
                --config inundate_breaches.yaml \
                --hgrid ../hgrid.gr3 \
                --out-dir .

The command writes four files that share the same generated geometry:

``depth_enforce_inundate.yaml``
        Breach dredging for a second ``prepare_schism`` pass.

``elev_inundate.yaml``
        Domain, dry-island and breach-pool rules used to generate ``elev.ic``.

``hydraulic_structures_inundate.yaml``
        Temporary structures, plus ``.th`` schedules when breach dates are supplied.

``inundate_regions.yaml``
        Complete regions for the continuation hotstart's ``patch_init``.

Apply the depth, elevation and structure files in a second preprocessing pass
whose mesh input is the finished base ``hgrid.gr3``. This preserves the base
preprocessing result and makes the restoration modification reproducible. If
the depth changes warrant a refitted vertical grid, regenerate it in this pass
and build the hotstart against that new vertical grid.

For elevation in the continuation hotstart, point ``patch_init`` directly at
``inundate_regions.yaml``. Use the prior ``hotstart_nc`` in ``domain`` and the
generated ``elev.ic`` in every restoration region::

        elevation:
            initializer:
                patch_init:
                    smoothing: false
                    regions_filename: ../inundate_regions.yaml
                    allow_overlap: true
                    allow_incomplete: false
                    regions:
                        - region: domain
                            initializer:
                                hotstart_nc:
                                    data_source: source_for_hotstart/hotstart.nc
                                    source_hgrid: source_for_hotstart/hgrid.gr3
                                    source_vgrid: source_for_hotstart/vgrid.in.3d
                                    source_vgrid_version: "5.10"
                                    max_blw_bed: 0.01
                                    novel_node_tol: 0.001
                        - region: restoration_area
                            initializer:
                                text_init:
                                    data_source: ../prepro_out_inundate/elev.ic

List ``domain`` first and every restoration region afterwards. The regions
overlap intentionally, ``allow_overlap`` is therefore required, and the last
matching configured region wins. Repeat the ``text_init`` entry for each named
restoration region generated by the tool. Transfer temperature, salinity,
velocities and turbulence variables from the prior hotstart in their own
``hotstart_nc`` initializers.

Validate the result against intent as well as file integrity: check the clock,
finite values, tracer ranges, restoration elevations, water-column depth
``dp + eta``, wet/dry state, and wet reference nodes for every hydraulic
structure. Regenerate the hotstart whenever the target ``hgrid``, ``vgrid``,
``elev.ic`` or region file changes.

Combining Hotstarts and Managing Restart Files
----------------------------------------------

In modern SCHISM workflows, combining hotstarts is a routine operation and no
longer something that should be done manually. The process has three steps:

1. Identify which hotstart (time step / date) you want.
2. Combine the per-processor hotstart files into one file.
3. Move it out of ``outputs/`` and give it a meaningful name.

Historically, this was done by hand using the native SCHISM utility
``combine_hotstart7`` (the trailing number varies by SCHISM version).  
A typical manual workflow looked like the following::

    cd outputs
    combine_hotstart7 -i 24000
    mv hotstart_it=24000.nc ../hotstart.20210515.24000.nc

This still works, but it requires you to know which iteration corresponds to
which calendar date and where to put the final file.  We now automate this
process for consistency and to reduce the chance of user error.

Hotstart Inventory Utility (``schimpy.hotstart_inventory``)
-----------------------------------------------------------

The ``hotstart_inventory`` tool reads the hotstart files in your ``outputs/``
directory and constructs a table linking:

* iteration (SCHISM time step),
* model datetime (based on ``run_start`` and ``dt``),
* and hotstart file availability.

This means you no longer need to calculate dates by hand.  For example::

    hotstart_inventory --workdir outputs

might print something like::

    2014-03-25T00:00:00    iteration 7200
    2014-03-25T12:00:00    iteration 10800
    2014-03-26T00:00:00    iteration 14400

The same utility is available from Python:

.. code-block:: python

    from schimpy.hotstart_inventory import hotstart_inventory
    df = hotstart_inventory(workdir="outputs")
    print(df)

This returns a ``pandas`` DataFrame indexed by datetime with one column,
``iteration``.  This date ↔ iteration mapping is also what powers the new
``combine_hotstart`` workflow described next.

Automated Hotstart Combining (``bdschism.combine_hotstart``)
------------------------------------------------------------

The ``bdschism`` CLI and library provide a wrapper around the native
``combine_hotstart7`` program.  The wrapper:

* finds the correct hotstart in the inventory,
* calls the SCHISM combine utility for the right iteration,
* renames the result using a consistent convention,
* optionally archives it, and
* optionally creates ``hotstart.nc`` in the run directory for restart runs.

This avoids the need to enter ``outputs/`` manually or guess iteration numbers.

File Naming Convention
^^^^^^^^^^^^^^^^^^^^^^

The wrapper names combined hotstarts as::

    hotstart[.PREFIX].YYYYMMDD.ITER.nc

Examples::

    hotstart.20240312.14400.nc
    hotstart.clinic.20240312.14400.nc

The optional ``PREFIX`` is useful when creating multiple hotstarts for different
scenarios (e.g., ``clinic`` vs. ``tropic`` configurations).

Typical Use Cases
^^^^^^^^^^^^^^^^^

**1. Get the latest hotstart and make it the restart file**

.. code-block:: bash

    combine_hotstart --latest --link --prefix clinic

This creates ``hotstart.clinic.YYYYMMDD.ITER.nc`` in the run directory and a
link named ``hotstart.nc`` pointing to it (required for ``ihot=2`` restarts).

**2. Choose the last hotstart on or before a specific date**

.. code-block:: bash

    combine_hotstart --before 2014-03-26 --prefix retro

Useful for runs aligned with field observations (e.g., USGS cruises).

**3. Combine a specific iteration**

.. code-block:: bash

    combine_hotstart --it 14400 --out-dir hotstart_archive --prefix retro

**4. Archive every Nth hotstart**

.. code-block:: bash

    combine_hotstart --every 10 --out-dir hotstart_archive

This writes only selected hotstarts (10th, 20th, …) into ``hotstart_archive/``.

### Python API

You may also use the wrapper programmatically:

.. code-block:: python

    from bdschism.combine_hotstart import combine_hot

    files = combine_hot(
        run_dir=".",
        outputs_dir="outputs",
        prefix="clinic",
        latest=True,
        link=True,
    )

This returns a list of absolute paths to the newly created combined hotstarts.

Why This Matters
----------------

Combined and dated hotstart files serve three roles:

* They document model readiness at specific points in time.
* They allow reruns and branching studies without repeating long spinups.
* They provide stable initial conditions when modules are changed or new
  alternatives are introduced.

The ``bdschism.combine_hotstart`` workflow standardizes naming, reduces errors,
and maintains a clean audit trail of how and when hotstarts were created.

``combine_hotstart`` is now the recommended way to prepare restart files for all
production SCHISM runs.

``ihot=2`` in ``param.nml`` continues to be the SCHISM-side “restart mode”, but
the management and naming of hotstart files is handled entirely outside the
model via this utility.




