# Test Suite

## Overview

The test suite is used with a complete SCHISM setup to test for any issues that might impact a simulation. When used, it runs through all tests marked in the test_suite directory. See documentation [here](https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/topics/run_tests.html).

## Example Use

1. Navigate to your SCHISM model directory
2. Activate a conda environment that has pytest and bdschism in it
3. run pytest *PATH TO BayDeltaSCHISM/test_suite* --sim_dir=.

This will show a list of warnings and errors which may impact your simulation success.

## Tests in Suite
| Test Script Name    | Description                                                                           |
|---------------------|---------------------------------------------------------------------------------------|
| test_elev2d.py      | - Check that the start time of elev2d matches the start time of param.nml             |
|---------------------|---------------------------------------------------------------------------------------|
| test_nudging.py     | - Iterate through all nudging files being used (from param.nml) and test              |
|                     |   that the .gr3 and .nc suffixes are consistent                                       |
|                     |     - e.g. SAL_nudge_roms.gr3 and SAL_nu_roms.nc                                      |
|---------------------|---------------------------------------------------------------------------------------|
| test_smscg.py       | - Check that boatlock is open when radial gates are tidally operated                  |
|                     | - Check that flashboards are closed when radial gates are tidally operated            |
|                     | - Check that tidal operation makes sense (upstream open/downstream closed)            |
|                     | - Check that when radial gates are open that both downstream and upstream are open    |
|---------------------|---------------------------------------------------------------------------------------|
| test_source_sink.py | - Check source_sink.in matches number of sources/sinks in vsource.th/vsink.th         |
|                     | - Check that source/sink .th duration spans the simulation period                     |
|                     | - Check that the units *seem* to fit the right range                                  |
|---------------------|---------------------------------------------------------------------------------------|
| test_vgrid.py       | - Check for any 0-layer cells in the vgrid.in.3d file                                 |
|---------------------|---------------------------------------------------------------------------------------|


