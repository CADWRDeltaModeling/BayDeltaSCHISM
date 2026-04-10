================
Mesh Input File
================

The mesh input file can be either a `.2dm` or a `.gr3` file in order to work with schimpy's `prepare_schism` utility. The mesh input file contains the horizontal grid information, including the node coordinates and the connectivity of the elements.

The mesh input file is typically generated using a preprocessor tool, such as AquaVeo's SMS. This section will not discuss how to generate the mesh input file, but rather how to use it in the context of the BayDeltaSCHISM model setup. For information on generating the mesh input file, see the `Advanced topics: Gridding the Horizontal Mesh <gridding_mesh>`_ section.

2dms
-----

The 2dm format is a proprietary format used by AquaVeo's SMS software. We use SMS and 2dm formats for mesh generation and editing, and provide the most up-to-date mesh input files in the <PUT LINK TO 2dm FOLDER>.

The 2dm is strictly a horizontal mesh format with no additional information about boundaries or any other model input. It only contains nodes, edges, and elements as well as the connectivity between them.

The 2dm becomes useful to SCHISM when it is converted to an `hgrid.gr3` file using schimpy's `prepare_schism` utility. During preprocessing with prepare_schism, bathymetric data are added to the mesh as well as boundary edges and their indices. The `hgrid.gr3` file is the format that SCHISM uses for the horizontal grid.

hgrid.gr3
----------

The `hgrid.gr3` file is the horizontal grid file that SCHISM uses for its simulations. It contains information about the nodes, edges, elements, bathymetry, and boundaries of the mesh. Review SCHISM's documentation on the Horizontal grid `here <https://schism-dev.github.io/schism/master/input-output/hgrid.html>`_.

All other spatial inputs (e.g. manning.gr3, sav_N.gr3, diffmin.gr3, etc.) are generated based on the `hgrid.gr3` file during preprocessing. Therefore, one can't change the horizontal grid without regenerating all of the other spatial inputs. This is why we recommend using the preprocessor to implement changes to the mesh, as it will automatically regenerate all of the necessary files based on the new `hgrid.gr3` or `2dm` input file.