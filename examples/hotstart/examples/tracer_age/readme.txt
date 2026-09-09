tracer_age
Use hotstart.nc from a baseline run but add 'tracer' and 'age' variables. 
For tracer_age run, 'param.nml.clinic' is required, as this file gives information on how many tracers to be defined. 
For an ihot=2 continuation, keep run_start at the original simulation origin and set date to the restart moment. Schimpy computes time, iths, and nsteps_from_cold from those values and time_step; do not patch the generated clock variables manually.

The create_hotstart_tracer_age.py driver is a legacy example. Current work should declare modules in the YAML and run create_hotstart hotstart_tracer_age.yaml.
