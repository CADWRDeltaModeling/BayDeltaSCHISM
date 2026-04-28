

# Dependencies between our projects:

bdschism is housed inside: https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/. The user guide provides documentation on context for SCHISM
vtools refers to vtools3: https://github.com/CADWRDeltaModeling/vtools3. 
schimpy: https://github.com/CADWRDeltaModeling/schimpy


| Project         | Depends on                    | Notes                         | Purpose |
|-----------------|------------------------------|-------------------------------|----------------|
| vtools          | —                            | Core foundation               | Time series manipulation and tidal functionality |
| dms_datastore   | vtools                       | Stable                        | Retrieval and management of time series |
| schimpy         | vtools                       | Stable                        | Preprocessing general schism input useful to any SCHISM user |
| schimpy         | dms_datastore                | Transitional (no new)  |
| bdschism        | vtools, dms_datastore, schimpy, suxarray | All dependencies remain     |   Bay-Delta specific functionality (more hard wires) |

- Assume tool stack exists, no defense.
- Do not program indirect dependencies on HEC-DSS
- Do not add to the spatial dependency stack
- Do not add to the plotting dependency stack

# CLI
- If operating on data, have a funtion that does that with a worker function based on CLI. The CLI or a secondary wrapper should validate and open files. 
- CLI should have informative -h and --help 
- If CLI should uses logging, it should be set up in the cli entry point function and use logging_config. Typical arguments include --logdir, --debug, etc.
- The canonical example includes the guard in bdschism/__init__.py logging_config. 
- If the nature of the project allows, scripts should have a workhorse function that facilitates equivalent work with inputs and outputs 
- The suite uses a hierarchical CLI structure. Code needs entry in the local package pyproj.toml, __main__.py, and also in bdschism. Remind the user.

# Passing data
- In bdschism, prep scripts may know station and repo names
- prefer read_ts_repo(station_id, param, subloc, repo). 
- alternately use read_ts(file_or_pattern)
- Note that force_regular is usually True and that you should report and solve problems rather than revert for continuous data (typical AI antipattern) 
- Interfaces and repos guaranteee regularity, scripts do not need to do this. 
- The default repo for applied chores should be screened for continuous time series involving flow, ec, elev and should be structures for gates and barriers. 
- other useful readers are in read_ts()
- an antipattern is pd.read_ts(). This is a familiar fallback for AI but often omits flag handling, NA codes, # comments, lacks metadata.
- scripts may assume "back door" acquisition but should provide cli or config choices to allow acquisition using files. [TODO: provide tools for this]

# Common patterns/antipatterns working with data
- merging is the prioritized tiling or shuffling of data. ALWAYS use vtools.functions.merge.py fuunctiosn for this. They are all elevated to vtools top namespace. Make sure the names argument is understood
- tidal filtering should be done with `from vtools import cosine_lanczos; tsave = cosine_lanczos(ts,'40h')`. 
- Use lower case frequency codes 'min' 'h' 'd' 's'.
- interval operations should use compare_interval(dt0, dt1) and divide_interval(dt0, dt1)
- interval creation should not hardwire implementation dt = pd.timeDelta(...). Use days(1), hours(3) or pd.to_timedelta
- For interpolating daily or montly averages, vtools.functions.rhistconserve should be used. Positivity is preserved with lbound and elevated p parameter when needed


# Testing 
- Tests are in /tests and use pytest. Further tests are CI/AI specific
- There is a separate run testing suite in bdschism that isn't code test. Ignore for software dev.
- Use schism environment for testing formally or informally
- Tests requiring web connectivity should be marked "integration" using standard pytest markers
- Github actions should exclude integration tests but user launch with pytest tests should catch them


# Coding practice 
- Functions should be single purpose
- Functions should be testable. 
- Avoid inference as the sole means of use. For instance, it is OK to locate the start date by locating a param.nml file and parsing it but this should not be the only way to use the function. 
- Wrong argument recovery should be kept minimal. Use a fail fast approach with ValueErrors. Minimize jargonny use of "fail fast"
- Numpydoc. Repair when interface changes, otherwise preserve.
- bdschism coding should be cognizant of the config system.
- if code is in a package system that depends on schimpy, use schimpy/schism_yaml.
- if code is in dms_datastore, achieve near-parity with omegaconf 

# AI interaction
- Plan before coding
- Do not refactor outside of scope of chat conversation. Alert is good 
- Do not contract existing documentation

# SCHISM wrappers
- SCHISM wrappers use the Dynaconf config system through settings.py to avoid hardwiring of and to stabilize identity of the utilities, e.g. "combine_hotstart" rather than "combine_hotstart7"
- Assume that the utilities are on path with no elaborate defenses. 
- Wrapper functions should be able to infer simulation directory and context based on existence of param.nml or hgrid.gr3 or various output files. They should be runable, though perhaps tediously, by providing these explicitly.
- Link creation should also follow config.





