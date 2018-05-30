
Working with SMS
================

The preprocessing toolkit has some utilities that can help when working with 
Aquaveo SMS, the main form of mesh generation we use until we are
able to distrubute a sufficient open source mesh generator.

Converting an SMS mesh (2dm) file to gr3
----------------------------------------

The script that converts SMS mesh to SELFE gr3 format is available as a standalone script.

sms2gr3.py
^^^^^^^^^^
.. argparse::
    :module: sms2gr3
    :func: create_arg_parser
    :prog: sms2gr3.py


Getting SMS Polygons for Preprocessor
-------------------------------------

SMS is able to create mesh coverages that are not mesh generation hints, including
spatial properties maps whose polygons have "material properties". If you save the
coverage as a polygon shapefile, the script *material_poly.py* can help convert the
resulting shapefile to the preprocessor yaml format. At the time of writing we do
not have a tutorial example of this process.s

material_poly.py
^^^^^^^^^^^^^^^^

.. argparse::
    :module: material_poly
    :func: create_arg_parser
    :prog: material_poly.py



Visualizing detailed bathymetry inside SMS
------------------------------------------

Earlier versions (before 11.2) of SMS had bugs causing incorrect georefercing of DEMs
and very poor memory management. It was -- and probably still is -- impossible 
to efficiently assign elevations within the software for a large mesh. We have two scripts
that were designed to help with this problem: *clip_dems.py* and *stacked_dem_fill.py*. 

clip_dems.py
^^^^^^^^^^^^

.. argparse::
    :module: clip_dems
    :func: create_arg_parser
    :prog: clip_dems.py

The script clip_dems.py is used to create mini-DEMs on the fly that are small 
enough to be brought into the SMS environment as rasters without slowing it down too much. 
The same The:ref:`dem_list_file` is used here as elsewhere in the pre-processor.

The normal pattern of work is to zoom into the area of interst in SMS, save the
work area as a jpeg image and use it as the -image argument to *clip_dems.py*.
One cut DEM will be produced for each DEM on the *dem_list* file that intersects the 
work area, using file names in order of priority (0 highest). The cut DEMs would then 
be imported and visualized in SMS, ideally using "contours" as the viewing choice and a carefully crafted color map designed to focus on the elevations that are locally most important.

stacked_dem_fill.py
^^^^^^^^^^^^^^^^^^^

.. argparse::
    :module: stacked_dem_fill
    :func: create_arg_parser
    :prog: stacked_dem_fill.py

The script stacked_dem_fill.py is the one we use to populate a mesh with elevations.
It can be used on a 2dm file in which case the 


