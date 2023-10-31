# Bay-Delta SCHISM Sediment Calibration Inputs

This repository contains Bay-Delta SCHISM input templates for sediment calibration. The inputs are based on the base template from `templates/bay_delta` directory of `BayDeltaSCHISM` repository. This instruction is based on the grid version `v110`.

To learn about SCHISM and its inputs files, please refer to SCHISM manual. It can be found at [SCHISM wiki](http://ccrm.vims.edu/schismweb/schism_manual.html).

See CHANGES.md to find out changes.

(In the future, different scenarios are managed by forking and branching.)

## Prerequisites

This instruction is written for a Linux environment. The procedure is similar on other platforms.
### Python packages
- Preprocessing steps requires SCHISM Python package, `schimpy`. The source codes of `schimpy` is available at [GitHub](https://github.com/CADWRDeltaModeling/schimpy/).
- Another required package is `dms_datastore`, which is used to download time series from the web. The source code of `dms_datastore` is also available at [Github](https://github.com/CADWRDeltaModeling/dms_datastore).

### BayDeltaSCHISM
Clone or download `BayDeltaSCHISM` from [GitHub BayDeltaSCHISM](https://github.com/CADWRDeltaModeling/BayDeltaSCHISM) in a separate directory. It contains common input files. This directory will be referred to as `BayDeltaSCHISM` in the following instructions.

## How to prepare and run the SCHISM sediment simulation

### Create common input files.
Follow the steps below to prepare common model settings.

  - Create SCHISM native spatial input files.
    - Copy the layer files (`minmaxlayer_slr_0_mod105.*`) from `BayDeltaSCHISM/template/bay_delta/` into the working directory.
    - Obtain a 2dm mesh file (e.g. `bay_delta_110_hist.2dm`) from TBD and copy it to the working directory.
    - Run `prepare_schism main_bay_delta.yaml` in your command line (or shell). You may need to edit the yaml file according to your setting. (Activate the Python environment with `schimpy` before running the script if `schimpy` is installed in a Python environment.) The whole process can take a couple of hours. This step will populate SCHISM native spatial input files such as `.gr3` and `.prop`.
  - Create gate and boundary time series files, as well as source and sink files.
    - Copy `BayDeltaSCHISM/bdschism/bdschism/multi_clip.py` into the working directory.
    - Open the file and specify the file path (bds_home) and start date as necessary.
    - Run `multi_clip.py`.
  - Create an ocean surface boundary time series file, `elev2D.th.nc`.
    - Copy `BayDeltaSCHISM/bdschism/bdschism/elev2D.bat` into the working directory.
    - Open the batch file and specify the values for the function arguments.
    - Run the batch file. In a Linux environment, use `bash elev2D.bat`.
  - Generate links to atmospheric data
    - Create `sflux` folder, and copy `sflux_inputs.txt` and `make_links_full.py` from `BayDeltaSCHISM/template/bay_delta/` into it.
    - Navigate into the `sflux` folder, and run `make_links_full.py`. The file contains hard-wired dates and locations of data files for DWR HPCs. Modify the script as necessary.
    - Remove the descriptive suffixes from the filenames for `msource.th`, `vsource.th`, and `vsink.th`.
  - Navigate back into the working directory and generate `station.in` by running `station` in schimpy environment.

### Run a 2D hydrodynamics simulation.
  - Create `outputs` directory if it does not exists.
  - Copy or create a link to `param.nml.2d` as `param.nml`.
  - Copy or create a link to `bctides.in.2d` as `bctides.in`.
  - Copy or create a link to `vgrid.in.2d` as `vgrid.in`.
  - Run SCHISM.
    - Typically, a SCHISM run is submitted to a job scheduler. An example of a PBSPro job submission script is provided in `launch.pbs*`. For the 2D run, refer to `launch.pbs.2d`. You may need to modify the script according to your environment.

### Prepare a 3D hydrodynamics-sediment simulation.
  - Create a ocean velocity boundary condition file, `uv3D.th.nc`.
    - Run `interpolate_variables8` inside `outputs` directory (make sure SCHISM module has been loaded).
      - Copy `BayDeltaSCHISM/template/bay_delta/interpolate_variables.in` into the 2D outputs directory.
      - Copy or link to `hgrid.gr3` in the 2D outputs directory as  `fg.gr3` and `bg.gr3`
      - Copy or link to `vgrid.in.3d` in the 2D outputs directory as `vgrid.fg`.
      - Run `interpolate_variables8` in the 2D outputs directory. It will generate `uv3D.th.nc`. If segmentation fault error is encountered, run `ulimit -s unlimited` first in the command line to increase the stack memory limit.
      - Move `uv3D.th.nc` to the study directory for the following step for a 3D simulation.
  - Create temperature and salt nudging files.
    - Run `prepare_nudging_data.py` in `scripts` directory, to compile data with which SCHISM solutions will be nudged.
    - Run `create_nudging.py` in `scripts` directory (this process may take up to several hours depending on the number of stations and undine period)
    - Rename the temperature nudging file created as TEM_nu.nc and move it to the parent directory.
    * If nudging is not used, related inputs in param.nml need to be modified accordingly.
  - Add sediment information to input files. Some of the input files used in the previous steps do not include sediment information, and sediment information needs to be augmented as follows:
    * Add sediment information to `msource.th` by running `add_sed_to_msource.py`: Run `python scripts/add_sed_to_msource.py --n_sediments 3` in the study directory. This will create `msource_sed.th` with island return flow sediment concentrations that use ambient suspended sediment concentrations. Rename `msource_sed.th` to `msource.th`.
  - Create an initial condition file, `hotstart.nc`:
    - First, navigate into `scripts` directory, then run `hotstart_get_time_slice.py` to generate timeseries pertaining to the Delta.
    - In the working directory, create a link to `sediment.nml.3d` as `sediment.nml`.
    - Run `create_hotstart_sed.py` in the working directory.
    - Rename `hotstart_sed.nc` to `hotstart.nc`. Be careful as not to overwrite existing `hotstart.nc`.

### Run the 3D hydrodynamics with sediment option.
  - Create an new `outputs` directory. If it exists already, e.g. for a 2D run, rename it. Otherwise, data in `outputs` will be overwritten by a simulation.
  - Copy `bctides.in.3d` into `bctides.in` for the 3D setting. (Or create a file link.)
  - Copy `vgrid.in.3d` into `vgrid.in` for the 3D setting. (Or make a file link).

#### Run a sediment bed composition generation (BCG) simulation
  - Run SCHISM with the sediment for sediment bed composition generation (BCG). (The binary name has `SED` in the suffix.)
    - Create a link to `param.nml.bcg` as `param.nml`.
    - Create a link to `sediment.nml.bcg` as `sediment.nml`.
    - Note: `rnday`=30 (`param.nml`) and `morph_fac`=100 (`sediment.nml`) will give 3000 effective days of simulation, consistent with van der Wegen et al. (2010).
    - Run the SCHISM sediment model for BCG.
    - After the run, you may want to rename `outputs` directory to `outputs_bcg`.
    - Navigate into the BCG outputs directory, and combine the last hotstart outputs using combine_hotstart7 (make sure SCHISM module has been loaded)
      - For example, if the target hotstart file's name ends with _28800.nc, run:  `combine_hotstart7 -i 28800`
    - Copy sediment bed information from the BCG run to the existing hotstart file. Run a script as follows in the top of the directory to add the bed fraction information. (you may need to change file names accordingly): `python scripts/copy_bed_fraction.py --hotstart_input hotstart.nc --hotstart_bcg outputs_bcg/hotstart_it=28800.nc --hotstart_output hotstart_with_bcg.nc`.
    - Rename the new hotstart to `hotstart.nc`.

#### Run a SCHISM run with the sediment
  - Run SCHISM with the sediment.
    - Create a link to `param.nml.3d` as `param.nml`.
    - Create a link to `sediment.nml.3d` as `sediment.nml`
    - Create an `outputs` directory.
    - Run the SCHISM sediment model, for example: `qsub launch.pbs.sed`

## Contact
Please contact Kijin Nam at <knam@water.ca.gov> or Hans Kim at <Hansang.Kim@water.ca.gov> for questions.
