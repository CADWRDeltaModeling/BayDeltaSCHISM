# Bay-Delta SCHISM Sediment Calibration Inputs

This repository contains Bay-Delta SCHISM inputs for sediment calibration. The inputs are based on the template from the `BayDeltaSCHISM` repository, and the version number of the template is `v110`.

To learn about SCHISM and its inputs files, please refer to SCHISM manual. It can be found at [SCHISM wiki](http://ccrm.vims.edu/schismweb/schism_manual.html).

See CHANGES.md to find out changes.

(In the future, different scenarios are managed by forking and branching.)

## Prerequisites
### Python packages
- Preprocessing steps requires SCHISM Python package, `schimpy`. The source codes of `schimpy` is available at [GitHub](https://github.com/CADWRDeltaModeling/schimpy/).
  - It is recommended that `schipmy` is installed in an environment that supports Anaconda and python 3 features on HPC (http://dwrrhapp0179.ad.water.ca.gov/gitea/knam/hpc2_conda_environments)
  - To install `schimpy`, first navigate to the folder containing the source code, then type in
  ``
  git checkout 5f6eb51
  ``
  to select the correct version is installed. Then, type in
  ``
  pip install -e .
  ``
- Another required package is `dms_datastore`, which is used to download time series from the web. The source code of `dms_datastore` is also available at [Github](https://github.com/CADWRDeltaModeling/dms_datastore).
  - To install `dms_datastore`, first navigate to the folder containing the source code, then type in
  ``
  git checkout fe52928
  ``
  to select the correct version is installed. Then, type in
  ``
  pip install -e .
  ``

### BayDeltaSCHISM
Clone or download `BayDeltaSCHISM` from [GitHub BayDeltaSCHISM](https://github.com/CADWRDeltaModeling/BayDeltaSCHISM) in a separate directory. It contains supplemental input files.

## Note
This README and scripts in the repositories are mainly intended to run on our HPCs.

## How to prepare and run the simulation

### Create common input files
Follow the steps below to prepare common model settings.

  - Create SCHISM native spatial input files.
    - Copy the layer files (`minmaxlayer_slr_0_mod105.\*`) from `BayDeltaSCHISM/template/bay_delta/` into the working directory.
    - Copy the mesh file (`bay_delta_110_hist.2dm`) from `//nasbdo/schism/mesh_files/` into the working directory.    
    - Run `prepare_schism main_bay_delta_hpc.yaml` in your command line (or shell). (Activate the Python environment with `schimpy` before running the script if `schimpy` is installed in a Python environment.) The whole process can take a couple of hours. This step will populate SCHISM native spatial input files such as `.gr3` and `.prop`.
      * If this step is performed on a Delta Modeling Section office Windows machine, use `main_bay_delta.yaml` instead of `main_bay_delta_hpc.yaml`.
  - Create gate and boundary time series files, as well as source and sink files.
    - Copy `BayDeltaSCHISM/bdschism/bdschism/multi_clip.py` into the working directory.
    - Open the file and specify the file path (bds_home) and start date as necessary.
    - Run `multi_clip.py`.
  - Create an ocean surface boundary time series file, `elev2D.th.nc`.
    - A script in the following steps uses tools from `schimpy`. Please set up the package in your Python environment.
    - Navigate into `scripts` directory, and run `generate_elev2d.py`.
  - Generate links to atmospheric data
    - Create `sflux` folder, and copy `BayDeltaSCHISM/template/bay_delta/sflux_inputs.txt` into it.
    - Navigate into the `sflux` folder. Run `BayDeltaSCHISM/template/bay_delta/make_links_full.py`. The file contains hard-wired dates and locations of data files for DWR HPCs. Update the codes if necessary.
  - Generate `station.in` by running `station` in schimpy environment.

### Run a 2D hydrodynamics simulation.
  - Create `outputs` directory if it does not exists.
  - Copy or create a link to `param.nml.2d` as `param.nml`.
  - Copy or create a link to `bctides.in.2d` as `bctides.in`.
  - Copy or create a link to `vgrid.in.2d` as `vgrid.in`.
  - Run SCHISM.
    - On HPC4, use `schism/5.10_intel2022.1` module. It comes with a few variants of schism binaries, and `pschism_PREC_EVAP_GOTM_TVD-VL` can be used for this 2D mode run.

### Prepare a 3D hydrodynamics-sediment simulation.
  - Create `uv3D.th.nc`
    - With SCHISM v5.10, it is no longer required to combine variables.
    - Run `interpolate_variables8` inside `outputs` directory (make sure SCHISM module has been loaded).
      - Copy `interpolate_variables.in` into the 2D outputs directory.
      - Copy or link to `hgrid.gr3` in the 2D outputs directory as  `fg.gr3` and `bg.gr3`
      - Copy or link to `vgrid.in.3d` in the 2D outputs directory as `vgrid.fg`.
      - Run `interpolate_variables8` in the 2D outputs directory. It will generate `uv3D.th.nc`. If segmentation fault error is encountered, run `ulimit -s unlimited` first.
      - Move `uv3D.th.nc` to the study directory for the following step for a 3D simulation.
  - Create temperature and salt nudging files
    - Run `prepare_nudging_data.py` in `scripts` directory, to compile data with which SCHISM solutions will be nudged.
    - Run `create_nudging.py` in `scripts` directory (this process may take up to several hours depending on the number of stations and nuding period)
    - Rename the temperature nudging file created as TEM_nu.nc and move it to the parent directory.
    * If nudging is not used, related inputs in param.nml need to be modified accordingly.
  - Add sediment information to input files. Some of the input files used in the previous steps do not include sediment information, and sediment information needs to be augmented as follows:
    * Add sediment information to `msource.th` by running `add_sed_to_msource.py`: Run `python scripts/add_sed_to_msource.py --n_sediments 3` in the study directory. This will create `msource_sed.th` with island return flow sediment concentrations that use ambient suspended sediment concentrations. Rename `msource_sed.th` to `msource.th`.
  - Create an initial condition file, `hotstart.nc`:
    - Run `create_hotstart_sed.py`.
      - First, navigate into `scripts` directory, then run `hotstart_get_time_slice.py` to generate timeseries pertaining to the Delta.
      - Following files are also required (specified in `hotstart_sed.yaml`):
        - `usgs_cruise_station.txt`: It is available from the `BayDeltaSCHISM` repository. The file is copied to `scripts` for convenience.
        - `usgs_2015_11_18.txt`: Field data from the USGS Polaris cruise. This one can be found in `scripts` directory.
    - Rename `hotstart_sed.nc` to `hotstart.nc`. Be careful as not to overwrite existing `hotstart.nc`.

### Run the 3D hydrodynamics with sediment option.
  - Create a new `outputs` directory. If it exists already, e.g. for a 2D run, rename it. Otherwise, data in `outputs` will be overwritten by a simulation.
  - Copy `bctides.in.3d` into `bctides.in` (Or make a link).
  - Copy `vgrid.in.3d` into `vgrid.in` (Or make a link).
  - Run SCHISM with the sediment for sediment bed composition generation (BCG). (The binary name has `SED` in the suffix.)
    - Create a link to `param.nml.bcg` as `param.nml`.
    - Create a link to `sediment.nml.bcg` as `sediment.nml`.
    - Note: `rnday`=30 (`param.nml`) and `morph_fac`=100 (`sediment.nml`) will give 3000 effective days of simulation, consistent with Wegen et al. (2010).
    - Run the SCHISM sediment model for BCG.
    - After the run, you may want to rename `outputs` directory to `outputs_bcg`.
    - Navigate into the BCG outputs directory, and combine the last hotstart outputs using combine_hotstart7 (make sure SCHISM module has been loaded)
      - For example, if the target hotstart file's name ends with _28800.nc, `combine_hotstart7 -i 28800`
    - Copy sediment bed information from the BCG run to the existing hotstart file. Run a script as follows in the top of the directory (you may need to change file names accordingly): `python scripts/copy_bed_fraction.py --hotstart_input hotstart.nc --hotstart_bcg outputs_bcg/hotstart_it=28800.nc --hotstart_output hotstart_with_bcg.nc`. Rename the new hotstart with the updated bed composition to `hotstart.nc`.
  - Run SCHISM with the sediment.
    - Create a link to `param.nml.3d` as `param.nml`.
    - Create a link to `sediment.nml.3d` as `sediment.nml`
    - Create an `outputs` directory.
    - Run the SCHISM sediment model for BCG.

## Contact
Please contact Kijin Nam <knam@water.ca.gov> for questions.

