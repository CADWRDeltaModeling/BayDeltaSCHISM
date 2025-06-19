
.. _param:

##############################
Key Run Parameters and Gotchas
##############################

The param.nml from SCHISM is mostly well-commented and documented. But here are some often-modified parameters.

Runtime settings
----------------

Hotstart settings
-----------------

Nudging settings
----------------

To determine which modules receive nudging, the param.nml looks for `inu_tr(n)`, where `n` is the Module number. The default configuration is:

.. list-table:: SCHISM Tracer Modules
   :header-rows: 1
   :widths: 10 30 20

   * - Module Number
     - Variable
     - Module Name
   * - 1
     - Temperature
     - TEM
   * - 2
     - Salinity
     - SAL
   * - 3
     - Generic Tracer
     - GEN
   * - 4
     - Age
     - AGE
   * - 5
     - Sediment 3D
     - SED3D
   * - 6
     - EcoSim
     - ECOSIM
   * - 7
     - ICM
     - ICM
   * - 8
     - CoSINE
     - COSINE
   * - 9
     - FIB
     - FIB
   * - 10
     - TIMOR
     - TIMOR
   * - 11
     - FABM
     - FABM

For more details on nudging in SCHISM, see :ref:`nudging`.

Output requests
---------------

Settings that have historically gone awry
-----------------------------------------


What happens when SCHISM versions get advanced?
-----------------------------------------------

