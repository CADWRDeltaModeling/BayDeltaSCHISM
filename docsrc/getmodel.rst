
.. _getstarted:

================================
Installation And Getting Started 
================================

Overview
--------

Depending on your experience level, you may be installing a bunch of tools, learning a 
new computation environment and/or getting acquainted with a new model. Our experience is that
folks who take all of that on together tend to struggle. Here are ways you can break it:

  - This page lists the main items you will need to install or acquire.
  - Don't mix learning the model and learning Linux if you are still familiarizing. Download the model and try the first couple tutorials on `Hello SCHISM <https://cadwrdeltamodeling.github.io/HelloSCHISM/>`_
    a simplified grid using Windows if that is your platform of preference. See the :doc:`learning`. 
  - Be aware of the `learning resources    <https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/learning.html>`_ page which is the hub for documentation for the project.
  - In particular, there is a :doc:`user_guide`. It contains details on how we set up the Bay-Delta SCHISM application, and the table of contents is a good reminder even for experienced users. 
  - Explore the Python tools listed below. We will happily answer questions about what tools are available to avoid constant reinvention of the same functionality.  
  - If you have just set up the model in a new computing environment, benchmark it on a working example. Download the code and the ready-to-run :ref:`complete-sample` and use them to configure and test your target high performance computing (HPC) environment.

SCHISM Code or Binaries
-----------------------

Downloading
^^^^^^^^^^^

How you will obtain the model code depends on the operating system. If you are working on Windows (which is mostly useful for instruction or reduced size problems), compatible `Windows binaries <https://msb.water.ca.gov/documents/86683/266737/schism_4.1_bin_windows.zip>`_ are available. This will underperform compared to a Linux cluster. For that, clone the SCHISM source code from the schism-dev GitHub `repository <https://github.com/schism-dev>`_ and compile it for your high performance system. Manuals and build instructions are available on the `SCHISM Web Site <http://ccrm.vims.edu/schismweb/>`_ 

Compile Settings
^^^^^^^^^^^^^^^^

We compile for Linux using CMake using the SCHISM 
`instructions for cmake <https://schism-dev.github.io/schism/master/getting-started/compilation.html>`_

The bulk of the work is making sure you have a compiler and links to the required libraries. 

For basic hydro-salinity runs we use the following cmake settings for which you will have to modify where GOTM is (also note our basic calibration doesn't use GOTM): 

::

  $ cmake ../src -DPREC_EVAP=ON -DTVD_LIM=VL -DUSE_GOTM=ON -DGOTM_BASE=~/myscratch/gotm_home

Additional settings are needed to model age, sediment, biogeochemistry.

Git
---

Our materials are mostly distributed on our `GitHub organization page <https://github.com/CADWRDeltaModeling>`_

You will need Git. Instructions are widely available
online. The basic operation on the command line for cloning a repository looks like this:

:: 

  git clone https://github.com/CADWRDeltaModeling/BayDeltaSCHISM.git

Bay-Delta Package
-----------------

Clone the `Bay-Delta Package on GitHub <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM>`_

The package includes a simulation template corresponding to the calibration, preprocessing tools and several of the tutorials that we will be using in the January hands-on Bay-Delta workshop. Help on the preprocessor and model setup can be found in the `schimpy <https://cadwrdeltamodeling.github.io/schimpy>`_ documentation. The package includes a /bin directory that needs to be populated by building the source or grabbing windows binaries if you want to learn on a high quality pc. 

The current temporal coverage is calendar 2008-2023. There are several items in the distribution that are large and binary and distributed on the CNRA open data portal:
  * `SCHISM-compatible atmospheric data <https://data.cnra.ca.gov/dataset/bay-delta-schism-atmospheric-collection-v1-0>`_ which includes interpolated field data for wind, air pressure, and specific humidity, as well as reformatted `North American Regional Reanalysis results <https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/north-american-regional-reanalysis-narr>`_ for radiation and precipitation. 
  * `CenCOOS ROMS model output <https://data.cnra.ca.gov/dataset/bay-delta-schism-coastal-roms-dataset-for-boundary-relaxation-draft>`_ for forcing salinity and temperature on the boundary
  * `Processed bathymetry data <https://data.cnra.ca.gov/dataset/bay-delta-schism-processed-bathymetry>`_ for populating the model. This is based on our `Version 4.2 Bay-Delta Bathymetry release <https://data.cnra.ca.gov/dataset/san-francisco-bay-and-sacramento-san-joaquin-delta-dem-for-modeling-version-4-2>`_ with added smoothing steps to eliminate subgrid curvature (it preserves slope). 

Updates and transitions occur over the years. For instance, after 2020 we have moved from our own interpolated product to NOAA's HRRR reanalysis product for wind.
Also in 2020, we moved to Hycom for coastal salinity and temperature and other air properties (humidity, etc) and to Hycom for coastal data. We
are still in the process of making these materials public and as we do so superseded links will carry messages.

One of the most common questions we get is "what is the official package". If you are starting with SCHISM 
we recommend using the master branch of the repository for the latest (somewhat beta) product or, 
if replicability is paramount, a Git tagged version. It is always appropriate to ask this question. Our goal is that the sum of the VIMS code, our repo and the "big" data
sources are enough not only to grid the model but also to do things 

Required Python Packages
------------------------

Our preprocessor is Python based. 
We recommend, and only support, `conda <https://docs.conda.io/en/latest/>`_ for package management. 
Please avoid Anaconda; it is too big 
and we can't ensure compatibility between all the libraries if you include that much stuff. 
Instructions for managing Python environments are on our general Delta Modeling documentation page for Python. 

You will want the following tools:

  * schimpy [`schimpy project docs <https://cadwrdeltamodeling.github.io/schimpy>`_] [`schimpy code repo <https://github.com/CADWRDeltaModeling/schimpy>`_] for managing spatial inputs and templates plus utilities
  * vtools3  [`vtools3 project docs <https://cadwrdeltamodeling.github.io/vtools3/>`_] [`vtools3 code repo <https://github.com/CADWRDeltaModeling/vtools3>`_] for time series manipulation
  * dms-datastore [`dms-datastore project docs <https://cadwrdeltamodeling.github.io/dms_datastore/html/index.html>`_] [`dms-datastore code repo <https://github.com/CADWRDeltaModeling/dms_datastore>`_] | for managing data from common Bay-Delta sources.

Work tends to expand in a predictable way and we recommend a broader environment available 
at the Bay-Delta SCHISM `repo <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/schism_env.yml>`_.
We can provide modest support for modern versions of the packages on fairly up-to-date Python platforms.


Configuration System
--------------------

Overview
^^^^^^^^

Bay-Delta SCHISM uses `Dynaconf <https://www.dynaconf.com/>`_ for settings management.

The bdschism scripts and command line utilities rely on a mix of convention and configuration.  For instance the schism utilities 
have version numbers like `interpolate_variables8` and we want to have a setting that captures that and then give it a simpler name
without constantly updating scattered python files.  

Configuration File Locations and Priorities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The system follows a prioritized hierarchy when loading configuration files:

1. **Environment-Specific Configuration**:
   - If the environment variable ``BDS_CONFIG`` is set and points to a valid configuration file, this file is loaded with the highest precedence.

2. **Project-Level Configuration**:
   - If a file named ``bds_config.yaml`` exists in the current working directory, it is loaded next, overriding the package defaults.

3. **Package Default Configuration**:
   - A default configuration file, located at ``config/bds_config.yaml`` within the package, serves as the fallback if no other configurations are provided.

The active configuration source is displayed during usage.

Usage
^^^^^

To retrieve the configuration settings, use:

.. code-block:: python

   from bdschism.setting import get_settings

   settings = get_settings()

You can then access configuration values as attributes:

.. code-block:: python

   link_style = settings.link_style["Windows"]
   interpolate_function = settings.interpolate_variables

Example Configuration File
^^^^^^^^^^^^^^^^^^^^^^^^^^

A partial ``bds_config.yaml`` file might look like:

.. code-block:: yaml

   link_style:
     Windows: copy   # options are 'copy' or 'junction'
     Linux: symlink  # Linux users should always use this

   # These are maps to the versioned names of utilities
   interpolate_variables: interpolate_variables10
   combine_hotstart: combine_hotstart7



Bathymetry
----------
The Bay-Delta Package already contains our latest bathymetry in geo-tiff form, processed as we use them to populate our mesh. Our bathymetry collection is available at the  
`CNRA open portal bathymetry page  <https://data.cnra.ca.gov/dataset/san-francisco-bay-and-sacramento-san-joaquin-delta-dem-for-modeling-version-4-2>`_. Note however, that what goes in the model is the `processed bathymetry <https://data.cnra.ca.gov/dataset/bay-delta-schism-processed-bathymetry>`_.


.. _complete-sample:

Complete Sample Inputs
----------------------

Interested users may want to explore their options as far as clusters 
and high performance environments without the confounding challenge of 
learning the preprocessor. 

A complete 21 day sample is under construction (March 2024).

VisIt SCHISM Plug-in
-----------------------
`VisIt <http://visit.llnl.gov/>`_ is a visualization toolkit for high performance 
numerical simulations. Note there is a visit-users forum and mailing list described at the 
`visit-users.org web site <http://visitusers.org/>`_. VisIt accesses specific data sources using plugins. At the time of writing, ours plugin works for SCHISM NetCDF UGRID 0.9 output from SCHISM. We do not distribute the base VisIt and since VisIt and the plugin version should be coordinated exactly.  

SCHISM plugins:
* `Source code  <https://github.com/schism-dev/schism_visit_plugin/archive/refs/tags/1.1.0.zip>`_
* `Compiled Windows binaries for 2.13.3 <https://github.com/schism-dev/schism_visit_plugin/releases/download/1.1.0/schism_plugin_visit2.13.3_win64_vs2012_tag_1.1.0.zip>`_
* `Compiled Windows binaries for 3.1.4 <https://github.com/schism-dev/schism_visit_plugin/releases/download/1.1.0/schism_plugin_visit3.1.4_win64_vs2017_tag_1.1.0.zip>`_
* `Compiled Windows binaries for 3.3.1 <https://github.com/schism-dev/schism_visit_plugin/releases/download/1.1.0/schism_plugin_visit3.3.1_win64_vs2017_tag_1.1.0.zip>`_

You may notice Visit documentation is becoming antiquated but still usable -- the software is supported by a vigorous wiki and forum on the `VisIt community site <http://visitusers.org>`_. We also offer the document `VisIT for SELFE users <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_instruction.pdf>`_

Links to tools
--------------

These are mostly Windows or Linux tools. If you have information
about analogous tools on other platforms we will gratefully share it.

* We use `Miniconda Python 3.9 through 3.11 64 bit <https://docs.conda.io/en/latest/miniconda.html>`_. If you use other package management methods you will have to intall our libraries from github and manage dependencies. 

* Tools like MobaXTerm or VS Code that can make terminal connections to linux clusters, in some cases using the x11 windows system which allows applications with windows. Note this recommendation has gotten old and many users now prefer VS Code. 

* `WinSCP <http://winscp.net/eng/index.php>`_ for transfering files to and from linux servers.




