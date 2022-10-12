
Getting Started 
===============

Depending on your experience level, you may be learning a 
new computation environment as well as a new model. 

  - This page lists the main items you will need to install or acquire.
  - Download the model and try the first couple tutorials on a simplified grid using Windows or Linux. See the :doc:`learning`. 
  - Try the Bay-Delta preprocessing tools `schimpy <https://cadwrdeltamodeling.github.io/schimpy>`_ in the package for working on the mesh, generating initial and boundary conditions, the ocean boundary and post processing. 
  - Download the code and the ready-to-run :ref:`complete-sample` and use them to configure and test your target high performance computing (HPC) environment.

SCHISM Code or Binaries
-----------------------

How you will obtain the model code depends on the operating system. If you are working on Windows (which is mostly useful for instruction or reduced size problems), compatible `Windows binaries <https://msb.water.ca.gov/documents/86683/266737/schism_4.1_bin_windows.zip>`_ are available. This will underperform compared to a Linux cluster. For that, clone the SCHISM source code from the schism-dev GitHub `repository <https://github.com/schism-dev>`_ and compile it for your high performance system. 

The SCHISM numerical methods are an extension of `SELFE v3.1dc <http://www.stccmop.org/knowledge_transfer/software/selfe>`_,
originally developed as a collaboration between Dr Joseph Zhang and Dr Antonio Baptista
while the two worked together at the Oregon Health & Science University. SCHISM contains critical optimizations and enhancements developed by Dr Zhang at the Virginia Institute of Marine Sciences, by the DWR Bay-Delta Office and by collaborators in other domains.

Bay-Delta Package
-----------------

* Clone the `Bay-Delta Package on GitHub <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM>`_

The package includes a simulation template corresponding to the calibration, preprocessing tools and several of the tutorials that we will be using in the January hands-on Bay-Delta workshop. Help on the preprocessor and model setup can be found in the `schimpy <https://cadwrdeltamodeling.github.io/schimpy>`_ documentation. The package includes a /bin directory that needs to be populated by building the source or grabbing windows binaries if you want to learn on a high quality pc. 

The current temporal coverage is calendar 2008-2018. There are several items in the distribution that are large:
  * `SCHISM-compatible atmospheric data <https://data.cnra.ca.gov/dataset/bay-delta-schism-atmospheric-collection-v1-0>`_ which includes interpolated field data for wind, air pressure, and specific humidity, as well as reformatted `North American Regional Reanalysis results <https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/north-american-regional-reanalysis-narr>`_ for radiation and precipitation. 
  * `CenCOOS ROMS model output <https://data.cnra.ca.gov/dataset/bay-delta-schism-coastal-roms-dataset-for-boundary-relaxation-draft>`_ for forcing salinity and temperature on the boundary
  * `Processed bathymetry data <https://data.cnra.ca.gov/dataset/bay-delta-schism-processed-bathymetry>`_ for populating the model. This is based on our `Version 4.2 Bay-Delta Bathymetry release <https://data.cnra.ca.gov/dataset/san-francisco-bay-and-sacramento-san-joaquin-delta-dem-for-modeling-version-4-2>`_ with added smoothing steps to eliminate subgrid curvature (it preserves slope). 

These are too big for GitHub and not text based. We are experimenting with GitHub's large data facility but for the momement after you download the package, you can deploy the command get_big_data.py from python. It will help you acquire what you need without manual downloads. 



VTools Scripting
----------------
Some pre/postprocessing tools are dependent on `VTools <https://cadwrdeltamodeling.github.io/vtools3/>`_.


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

`Complete 21-day sample inputs <https://msb.water.ca.gov/documents/86683/266737/preprocessed_sample.tar.gz>`_

includes a complete directory of inputs for a late August - early September 2013 baroclinic run with salt transport, sample PBS launching script (pbs.sh) and launching script (run.sh) that we use with our  cluster's job scheduler.


VisIt SCHISM Plug-in
-----------------------
`VisIt <http://visit.llnl.gov/>`_ is a visualization toolkit for high performance 
numerical simulations. Note there is a visit-users forum and mailing list described at the 
`visit-users.org web site <http://visitusers.org/>`_. VisIt accesses specific data sources using plugins. At the time of writing, ours plugin works for SCHISM NetCDF UGRID 0.9 output from SCHISM. We do not distribute the base VisIt and since VisIt and the plugin version should be coordinated exactly.  

SCHISM plugins:
* `Source code for 2.7 <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_1.0.0.source.zip>`_
* `Compiled Windows binaries for 2.7 <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_1.0.0_visit2.7_win64_vs2010.zip>`_
* `Compiled Windows binaries for 2.8 <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_1.0.0_visit2.8_win64_vs2012.zip>`_

You may notice Visit documentation is becoming antiquated but still usable -- the software is supported by a vigorous wiki and forum on the `VisIt community site <http://visitusers.org>`_. We also offer the document `VisIT for SELFE users <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_instruction.pdf>`_

Links to tools
--------------

These are mostly Windows or Linux tools. If you have information
about analogous tools on other platforms we will gratefully share it.

* We use `Miniconda Python 3.7 through 3.9 64 bit <https://docs.conda.io/en/latest/miniconda.html>`_. If you use other package management methods you will have to intall from github. 

* `Xming XServer for Windows <http://sourceforge.net/projects/xming/>`_ or other tools like MobaXTerm or VcXSrv for connecting to linux clusters using the x11 windows system. 

* `WinSCP <http://winscp.net/eng/index.php>`_ for transfering files to and from linux servers.




