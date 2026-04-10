==========================
Model Inputs & Generation
==========================

Overview of Model Inputs
-------------------------

Although we try to keep this documentation up-to-date, the absolute most up-to-date files and inputs are in `the templates folder in the GitHub repository <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/master/templates/bay_delta>`_.

For the core functionality of the model, there are three main categories of SCHISM inputs for the Bay-Delta model. These are:
* **Spatial Inputs and the Preprocessor**
* **Timeseries Inputs**
* **Spatio-Temporal Inputs**


Spatial Inputs and the Preprocessor
--------------------------------------

The preprocessor is a powerful tool for preparing spatial inputs, including the mesh and bathymetry, for your model run. It can be used to apply templates, modify existing runs, and configure input parameters through YAML files. 

.. toctree::
  :maxdepth: 2
  :titlesonly:

  mesh_input.rst
  preprocess.rst
  structures.rst
  vegetation.rst 

Timeseries Inputs
-------------------------

The timeseries inputs are the files that are not sensitive to the geometry of the mesh. These are generated from observed data for a hindcast.

.. toctree::
  :maxdepth: 2
  :titlesonly:

  baydelta_boundaries.rst
  ocean.rst
  flow_boundary.rst
  atmospheric.rst
  barotropic.rst
  param.rst  

Spatio-Temporal Inputs
-------------------------

Some files are sensitive to not only geometry but also time, such as the hotstart and nudging files which reference a specific start date and time. 

.. toctree::
  :maxdepth: 2
  :titlesonly:

  nudging.rst
  hotstart.rst