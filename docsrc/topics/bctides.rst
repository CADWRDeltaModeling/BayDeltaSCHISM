.. _bctides_topic:

Boundary Types (bctides.in)
===========================

``bctides.in`` tells SCHISM, for each open boundary, which variables are forced
and where each forcing comes from. The data themselves live elsewhere
(``flux.th``, ``elev2D.th.nc`` and so on); ``bctides.in`` only selects the type.
In the Bay-Delta workflow the file is generated from YAML by the schimpy
``bctide`` tool (or by the preprocessor), not edited by hand.

The full keyword reference, including every SCHISM type code and the checks
the tool performs, is in the schimpy chapter
:external+schimpy:ref:`Boundary conditions (bctides) <bctides>`.

Bay-Delta templates
-------------------

The `templates/bay_delta <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/templates/bay_delta>`_
folder holds the YAML for the standard runs:

* ``bctides.in.2d.yaml``: barotropic run (see :ref:`barotropic`).
* ``bctides.in.3d.yaml``: baroclinic run.
* ``bctides.in.sed.3d.yaml``: baroclinic run with three sediment classes.

The `examples/bctides <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/examples/bctides>`_
folder holds the same files plus ``bctides.in.3d.tide.yaml``, a synthetic
example that exercises tidal, constant, Flather and tracer options, and
``main_bctides.yaml``, which shows how the files are combined.

The standard baroclinic assignment is:

.. list-table::
   :header-rows: 1
   :widths: 24 16 15 15 30

   * - Boundary
     - flow_direction
     - elevation
     - velocity
     - temperature / salinity
   * - ``ocean``
     - bidirection
     - ``th_nc``
     - ``th_nc``
     - ``initial_profile``, nudge 0.01
   * - ``sjr``, ``sacramento``, ``yolo_toedrain``
     - inflow / bidirection
     -
     - ``th_text``
     - ``th_text``
   * - other tributaries (``coyote``, ``calaveras``, ``mokelumne``, ``american``, ``yolo``, ``napa``)
     - inflow
     -
     - ``th_text``
     - ``th_text`` temperature; constant salinity
   * - exports and diversions (``swp``, ``cvp``, ``ccc_*``, ``northbay``)
     - outflow
     -
     - ``th_text``
     -

``th_text`` selects the ASCII time history (``flux.th``, ``TEM_1.th``,
``SAL_1.th``) and ``th_nc`` the netCDF one (``elev2D.th.nc``, ``uv3D.th.nc``).
In the barotropic run the ocean keeps ``th_nc`` for elevation only, and the
other boundaries specify velocity only. ``uv3D.th.nc`` for the baroclinic
ocean boundary comes from the barotropic run (see :ref:`gen_uv3d`).

Outflow boundaries may not carry temperature, salinity or tracers, so the
sediment template assigns sediment only on inflow and bidirectional
boundaries.

Generating the files
--------------------

.. code-block:: console

   bctide main_bctides.yaml --logdir logs

The assignment chosen for every boundary is logged, which is a convenient check
that the template matches the intended run.
