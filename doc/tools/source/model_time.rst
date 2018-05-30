Model time conversion
=====================

The SELFE *.th file has two flavors, binary and text. Both are multicolumn formats,
with elapsed time in seconds in the left column since the start of the simulation
and the other columns representing values. 
There is no datum within the file to link elapsed time to calendar or geophysical time, 
and it is hard to search for events, re-use the *.th file with a different 
start date or make sense of orphaned files.

The *model_time.py* script is a utility that performs conversions between geophysical
and elapsed times. 

model_time.py
-------------

.. argparse::
    :module: model_time
    :func: create_arg_parser
    :prog: model_time.py
    