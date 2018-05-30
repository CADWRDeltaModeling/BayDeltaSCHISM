Performance Eval and Tuning
===========================

Subcycling analysis
-------------------

The *subcycle_analyzer.py* script analyzes output messages to find 
and map (as a *.prop file) the elements responsible for heavy amounts
of subcycling.

.. argparse::
    :module: subcycle_analyzer
    :func: create_arg_parser
    :prog: subcycle_analyzer.py

Plotting model performance
--------------------------

The *selfe_timing.py* plot is a simple time series plot showing the 
model speed calculated based on output plot timestamps.

.. argparse::
    :module: simulation_timing
    :func: create_arg_parser
    :prog: simulation_timing.py


