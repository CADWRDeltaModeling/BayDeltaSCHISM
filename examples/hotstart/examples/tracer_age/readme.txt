tracer_age
Use hotstart.nc from a baseline run but add 'tracer' and 'age' variables. 
For tracer_age run, 'param.nml.clinic' is required, as this file gives information on how many tracers to be defined. 
Also, note that if you wish to restart your SCHISM from the baseline hotstart time step (but with added 'tracer' and 'age' modules), you will need to change 'time' and 'nsteps_from_cold' in your hotstart.nc file to be consistent with those in the baseline hotstart file. By default, both 'time' and 'nsteps_from_cold' are zero in hotstart.nc. 
There are two ways to do it. 
1. you can directly read the generated 'hotstart.nc' and modify the above two variables. 
2. Or, you can combine only the tracer variables with the baseline hotstart.nc. The example code to perform this step is given in create_hotstart_tracer_age.py. 
