.. _userguide:

===========================
Bay-Delta SCHISM User Guide
===========================

The following topical guides take you through what it takes to set up a basic model run using the Bay-Delta SCHISM toolchain. You won't have action items on all the topics for every run, but the :ref:`Bay-Delta SCHISM Essentials <essentials>` section will get you started on a basic hindcast and the :ref:`Topical Guides <problems>` describe numerous common modeling tasks and where the gotchas are. 

See :ref:`Installation And Getting Started <getstarted>` for programatic setup and basic introductory materials.

Setup
-------------------------

.. toctree::
  :maxdepth: 3
  
  Running a Preprepared Setup <topics/processed_run>

________________________

.. _essentials:

Model Essentials
----------------------------

Overview
``````````````````````
.. toctree::
  :maxdepth: 3
  :titlesonly:

  topics/overview.rst
  topics/vignette.rst
  topics/files_and_directories  
  topics/preprocess.rst


Boundaries & Input Files
````````````````````````````````````
.. toctree::
  :maxdepth: 3
  :titlesonly:

  topics/ocean.rst
  topics/flow_boundary.rst
  topics/atmospheric.rst
  topics/barotropic.rst
  topics/param.rst  
  topics/hotstart.rst
  topics/nudging.rst
  topics/vegetation.rst 

Inspection of Model Setup
``````````````````````````
.. toctree::
  :maxdepth: 2
  :titlesonly:
 
  topics/checklists.rst
  topics/run_tests.rst
  
Output Files
````````````````
.. toctree::
  :maxdepth: 2
  :titlesonly:

  topics/output.rst  

________________________


Computing Resources
-----------------------------

.. toctree::
  :maxdepth: 4

  topics/hpc.rst
  topics/azure.rst
  topics/bds_guide_azure.rst


Advanced Tasks and Concepts
-----------------------------

.. toctree::
  :maxdepth: 2
  :titlesonly:
  
  topics/problems.rst
  topics/age.rst
  topics/sea_level_rise.rst
  topics/sources.rst
  topics/structures.rst
  topics/mesh.rst
  topics/utilities.rst
  
  



