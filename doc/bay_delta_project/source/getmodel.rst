
Getting Started 
===============

Depending on your experience level, you may be learning a new computation environment as well as a new model. We suggest you tackle these separately:

  - Download the model and try the first couple tutorials on a simplified grid using Windows or Linux. 
  - Try the Bay-Delta `preprocessing tools <scripting_tools/html/index.html>`_ in the package for working on the mesh, generating initial and boundary conditions, the ocean boundary and post processing. 
  - Download the code and the ready-to-run :ref:`complete-sample` and use them to configure and test your target high performance computing (HPC) environment.

SCHISM Code
-----------

Download `SCHISM source code <http://ccrm.vims.edu/schism/>`_. If you are working on Windows (which is mostly useful for instruction or reduced size problems), compatible 
`Windows binaries <https://msb.water.ca.gov/documents/86683/266737/schism_4.1_bin_windows.zip>`_ are available and can be used to populate the /bin directory of the Bay-Delta package.



The SCHISM numerical methods are an extension of `SELFE v3.1dc <http://www.stccmop.org/knowledge_transfer/software/selfe>`_,
originally developed as a collaboration between Dr Joseph Zhang and Dr Antonio Baptista
while the two worked together at the Oregon Health & Science University. SCHISM contains critical optimizations and enhancements developed by Dr Zhang at the Virginia Institute of Marine Sciences, by the DWR Bay-Delta Office and by collaborators in other domains.

Bay-Delta Package
-----------------

* `Download the Bay-Delta Package <https://msb.water.ca.gov/documents/86683/266737/bay_delta_schism.tar.gz>`_

The package includes a simulation template corresponding to the calibration, preprocessing tools and several of the tutorials that we will be using in the January hands-on Bay-Delta workshop. Help on the preprocessor and model setup can be found in the `preprocessor docs <http://baydeltaoffice.water.ca.gov/modeling/deltamodeling/models/tools/index.html>`_ which are also distributed with the package.
The package includes a /bin directory that needs to be populated by building the source. 

VTools Scripting
----------------
Some postprocessing tools are dependent on `VTools <http://baydeltaoffice.water.ca.gov/modeling/deltamodeling/models/vtools/index.html>`_.


Bathymetry
----------
The Bay-Delta Package already contains our latest bathymetry in geo-tiff form, processed as we use them to populate our mesh. The data are described on the 
`bathymetry page  <http://baydeltaoffice.water.ca.gov/modeling/deltamodeling/modelingdata/DEM.cfm>`_


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
numerical simulations. VisIt accesses specific data sources using plugins. At the time of writing, ours plugin works for SELFE/SCHISM native binaries and the next iteration will work for the NetCDF UGRID 0.9 output from SCHISM. We do not distribute the base VisIt. 

SCHISM plugins:
* `Source code for 2.7 <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_1.0.0.source.zip>`_
* `Compiled Windows binaries for 2.7 <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_1.0.0_visit2.7_win64_vs2010.zip>`_
* `Compiled Windows binaries for 2.8 <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_1.0.0_visit2.8_win64_vs2012.zip>`_

You may notice Visit documentation is becoming antiquated but still usable -- the software is supported by a vigorous wiki and forum on the `VisIt community site <http://visitusers.org>`_. We also offer the document `VisIT for SELFE users <https://msb.water.ca.gov/documents/86683/266737/visit_plugin_instruction.pdf>`_

Links to tools
--------------

These are mostly Windows or Linux tools. If you have information
about analogous tools on other platforms we will gratefully share it.

* `Anaconda Python 2.7 64 bit <https://store.continuum.io/cshop/anaconda/>`_

* `Xming XServer for Windows <http://sourceforge.net/projects/xming/>`_

* `WinSCP <http://winscp.net/eng/index.php>`_ for transfering files




