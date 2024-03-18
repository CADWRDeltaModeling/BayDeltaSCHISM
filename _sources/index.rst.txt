.. Bay-Delta SCHISM documentation master file, created by
   sphinx-quickstart on Fri Dec 05 22:53:35 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.




Bay-Delta SCHISM Project
========================

Welcome. This is home base for the Bay-Delta SCHISM modeling project.

Bay-Delta SCHISM is an application of the 3D open source `SCHISM <http://ccrm.vims.edu/schismweb/>`_ :cite:p:`zhang_new_2015` :cite:p:`zhang_seamless_2016` hydrodynamic and water quality suite to the San Francisco Bay Delta estuary. The project is a collaboration between the California Department of Water Resources and the Virginia Institute of Marine Sciences (VIMS).


Contents
--------

.. toctree::
  :maxdepth: 2
  :hidden:

  self
  
.. toctree::
  :maxdepth: 1

  getmodel
  learning
  user_guide
  calibration
  help
  refs


Independent manual web pages are available for `VTools <http://cadwrdeltamodeling.github.io/vtools3/>`_ and 
DWR's Python-based SCHISM Toolset `schimpy <https://cadwrdeltamodeling.github.io/schimpy/>`_.

  
Project description
-------------------

The goal of our project is to develop an open-source, cross-scale multidimensional model suitable to answer flow and water quality questions involving large extents of the Bay-Delta system over periods of several years. Target applications include: 
 * Habitat creation and conveyance options under Delta Conveyance Project;
 * Evaluation of conveyance pathways through Clifton Court to minimize transit time for fish
 * Computation of Low Salinity Zone and preferred habitat metrics in Suisun Marsh as part of the DWR's Incidental Take Permit and associated long term operations agreements;
 * Salinity intrusion changes under drought or sea level rise; 
 * Salinity benefits, water age and velocity changes following the installation of drought barriers; 
 * Fate of mercury produced in the Liberty Island complex; 
 * Provision of high resolution velocity fields for agent based (ELAM) modeling as part of structured decision making to improve salmon migration through the Sacramento River/Steamboat Slough area.


These applications vary a great deal in scope. Some can be studied with our base model with a few quick adjustments, but the last two require focal regions of intense study, multi-disciplinary biogeochemistry, or more careful validation of a particular transport mechanism. In our collaboration with NOAA and NASA in the SESAME project, the flexibility and openness of SELFE (forebearer of SCHISM) allowed swift incorporation of CoSINE, an alternate nutrient model to the standard EcoSIM 2.0 emphasizing the most important constituents for salmon in the system. 

Our immediate goal has been to establish a foundation – to develop a sense of global accuracy, requiring that we resolve (or craftily under-resolve) the main mechanisms of hydrodynamics and transport up the estuary and in Delta channels. These include gravitational circulation and exchange flow; periodic stratification; axial convergence; tidal trapping; flood-ebb asymmetry of flow paths, shear dispersion, primary flow streamlines, and perhaps some secondary circulation in large channels. 

Although we expect our general calibration to continue to improve, further work will be focus on project-dependent enhancements. Due to its flexible mesh, the model is easily re-usable in a near field/far field arrangement whereby the base model provides a pre-calibrated background grid for an extension or focal region of study. 

An overview of the Bay-Delta application is given in the `workflow guide <_static/workflow_guide.pdf>`_. Note this guide alludes to the "working title" as SELFE transitioned to SCHISM, SELFE-W.









Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

