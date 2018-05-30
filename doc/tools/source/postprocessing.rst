Post-processing
===============

Station Output Extractor
^^^^^^^^^^^^^^^^^^^^^^^^

SELFE can write outputs of certain model variables at given positions at every given time interval in a plain text format. The files of these outputs resides in 'outputs' directory under a study directory. File names of the outputs are named from 'staout_1' to 'staout_9,' and the files corresponds to surface elevation, air pressure, wind velocity in x- and y-direction, temperature, salinity, and velocity in x-, y-, and z-direction respectively. The positions of outputs are requested in 'station.in' in the study directory.

The station output extractor makes it easy to read these standard output files. It returns Vtools time series objects, which can be analyzed and plotted with some simple recipes.


Extracting Data from Binary outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Another way to extract values out of SELFE runs is extracting values from raw binary outputs. The upside of this approach is that users can extract anywhere they want after a run is finished if binary outputs are written, combined, and stored. The downside is the binary files are huge and possibly time-consuming. Extracting data from binary files currently relies on SELFE's own FORTRAN scripts.

