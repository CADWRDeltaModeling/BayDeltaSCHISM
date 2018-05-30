
Assigning bathymetry
====================

Converting a 2dm file to gr3 


.. argparse::
    :module: sms2gr3
    :func: create_arg_parser
    :prog: sms2gr3

Assigning depths from prioritized DEMs
--------------------------------------

stacked_dem_fill
^^^^^^^^^^^^^^^^
.. argparse::
    :module: stacked_dem_fill
    :func: create_arg_parser
    :prog: stacked_dem_fill


Smoother for complex topography
-------------------------------

Often it is necessary to incorporate inudated marshy areas where elevations
are poorly sampled and contours are tortuous. The script *contour_smooth.py*
uses min-max curvature flow (Malladi and Sethian) to impose a minimum length scale
of change for contours, essentially unraveling the features that are most contorted.
This script will be released soon.

.. contour_smooth.png



Optimizing depths for volume
----------------------------
A mesh draped over noisy bathymetry data does not necessarily represent important moments (volumes and vertical face areas) smoothly and realistically. To better represent these facets
of the geometry, we compare the volumetric quantities that come from SCHISM's shape functions (which are much like a TIN) to a higher order quadrature using the DEM with bilinear interpolation. The quadrature is more accurate, and also incorporates more sample points.


.. argparse::
    :module: grid_opt
    :func: create_arg_parser
    :prog: grid_opt







