.. |cbox|   unicode:: U+2610


===============
Horizontal Mesh
===============

The format of the SCHISM horizontal mesh is described in the `SCHISM manual <https://schism-dev.github.io/schism/master/index.html>`_. 

Users will find that SCHISM projects require refinement or extension. There are a few reasons:

- SCHISM modeling is often used for 
  
  - focused analysis, requiring refinement
  
  - sea level rise, requiring upstream extension or gridding of exposed areas.
  
  - restoration areas.
  
- The spatial parameterization is varied or parameterized, so there is no extensive "calibration" of a new mesh  


Here we will cover:

- Best practices for horizontal gridding

- Attaching boundaries

- :ref:`Checklist <change_mesh>` for after changing the grid or boundaries.

- Vertical grid.


.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none



Meshing
-------

Meshing considerations for SCHISM
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Video (Joseph Zhang, SCHISM summit)
"""""""""""""""""""""""""""""""""""

Video (Joseph Zhang #2)




Recap/checklist
"""""""""""""""


Getting to know SMS
^^^^^^^^^^^^^^^^^^^

Video (Eli Ateljevich)
""""""""""""""""""""""

Sample Data
""""""""""""

Recap checklist
"""""""""""""""

Presentation: clip_dems and efficient use of DEMS
"""""""""""""""""""""""""""""""""""""""""""""""""


Building the Bay-Delta mesh the standard way
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Presentation: Meshing consideration for marshes and restoration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Merging/Stitching SMS mesh/maps (new work, flooded islands, etc)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Video
"""""

Recap/checklist
"""""""""""""""



Vertical mesh setup
-------------------


.. _change_mesh:

Checklist for after you change the mesh
---------------------------------------

Changing the mesh tends to have consequences in places people forget to think about, though most are
straightforward or obvious. This is a checklist of gotchas that arise outside the gridding environment.

|cbox| Are boundaries still in the proper place?

|cbox| If boundaries moved, is depth enforcement preventing dry boundaries still in right place?

|cbox| Are flow cross sections in changed area still aligned?

|cbox| Are the node pairs that define hydraulic structure locations still correct?

|cbox| Are polygons used to define spatial inputs appopriate for new area?

|cbox| If grid was extended, do yaml polygons cover extended domain?

|cbox| Are sources excluded?

|cbox| Do you have submerged aquatic vegetation? Assumptions? Consider changing those file

|cbox| Old hotstarts not valid on new mesh, utilities will interpolate on new grid

|cbox| Old nudging files not valid on new mesh. Re-do.

|cbox| If refining/coarsening extensively on main channel, consider the effect on momentum and the algorithm.

|cbox| Mesh quality:

    |cbox| Skew and area warnings in preprocessor. 






