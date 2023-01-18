# Bay-Delta SCHISM Sediment Calibration Inputs

This repository contains Bay-Delta SCHISM inputs for sediment calibration. The inputs are based on the template from the `BayDeltaSCHISM` repository, and the version number of the template is `v110`.

To learn about SCHISM and its inputs files, please refer to SCHISM manual. It can be found at [SCHISM wiki](http://ccrm.vims.edu/schismweb/schism_manual.html).

See CHANGES.md to find out changes.

(In the future, different scenarios are managed by forking and branching.)

## Prerequisites
- Preprocessing steps requires SCHISM Python package, `schimpy`. The source codes of `schimpy` is available at [GitHub](https://github.com/CADWRDeltaModeling/schimpy/), and the package is available via Anaconda channel `cadwr-dms`.
  - It is recommended that `schipmy` is installed in an environment that supports Anaconda and python 3 features on HPC (http://dwrrhapp0179.ad.water.ca.gov/gitea/knam/hpc2_conda_environments)
- Clone or download `BayDeltaSCHISM` from [GitHub BayDeltaSCHISM](https://github.com/CADWRDeltaModeling/BayDeltaSCHISM) in a separate directory.

## Using DVC
To manage some large input files, the repository uses `DVC`. (See [DVC Website](https://dvc.org/) and [GitHub](https://github.com/iterative/dvc).) `DVC` is a Python package. When you use Anaconda, `DVC` can be installed by `conda install -c conda-forge dvc`. (Create a new Conda environment if you do not want to disturb your Conoda environments.) Refer to DVC GitHub README if you use different Python environments.

Cloning this repository would not pull data files that are managed by `DVC`. To pull data files from the `DVC` repository, just run `dvc pull` in case of running it on the DWR HPC's. (If you run `dvc pull` on Windows with access to the Section shared directory, try `dvc pull -r nasbdo`.)

## Note
This README and scripts in the repositories are mainly intended to run on our HPCs.

## How to prepare and run the simulation

### Create common input files
Follow the steps below to prepare common model settings.

  - Create SCHISM native spatial input files.
    - Run `prepare_schism main_bay_delta_hpc.yaml` in your command line (or shell). (Activate the Python environment with `schimpy` before running the script if `schimpy` is installed in a Python environment.) The whole process can take a couple of hours. This step will populate SCHISM native spatial input files such as `.gr3` and `.prop`.
      * If this step is performed on a Delta Modeling Section office Windows machine, use `main_bay_delta.yaml` instead of `main_bay_delta_hpc.yaml`.
    - It may be necessary to first run `dvc pull` to prepare grid files.
  - Create gate and boundary time series files, such as gate and flux `th` files using the data from `BayDeltaSCHISM` repository.
    - Run `prepare_th.py` at the top of the input directory as follows after replacing the location of `BayDeltaSCHIM` repository that you cloned somewhere else: `python scripts/prepare_th.py --dir_th __your_BayDeltaSCHISM_directory__ --list_of_th scripts/list_th.txt --start '2015-11-18'`. For example, if your BayDeltaSCHISM is cloned at `/home/foo/BayDeltaSCHISM`, the command would be `python scripts/prepare_th.py --dir_th /home/foo/BayDeltaSCHISM --list_of_th scripts/list_th.txt --start '2015-11-18'`. This will populate th files.
  - Create Delta depletion time series files
    * Run `prepare_th.py` at the top of the input directory similarly to the previous step but with a different list file as follows: `python scripts/prepare_th.py --dir_th dcd --list_of_th scripts/list_dcd.txt --start '2015-11-18'`. This will generate three th files: `vsource.th`, `vsink.th`, and `msource.th`.
  - Create an ocean surface boundary time series file, `elev2D.th.nc`.
    - A script in the following steps uses tools from `schimpy`. Please set up the package in your Python environment.
    - Navigate into `scripts` directory, and run `generate_elev2d.py`.
  - Navigate into `sflux` directory, and generate links to atmospheric data files by running `make_links.py`. (The file contains hard-wired dates and locations of data files for DWR HPCs. Update the codes if necessary.)

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
  - Run SCHISM with the sediment.
    - Create a link to `param.nml.3d` as `param.nml`.
    - Create a link to `sediment.nml.3d` as `sediment.nml`
    - Copy sediment bed information from the BCG run above. Run a script as follows. You may need to change according to your file names: `python scripts/copy_bed_fraction.py --hotstart_input hotstart.nc --hotstart_bcg outputs/hotstart_it=206400.nc --hotstart_output hotstart_with_bcg.nc`.
    - Rename the new hotstart with the updated bed composition to `hotstart.nc`.
    - Create an `outputs` directory.
    - Run the SCHISM sediment model for BCG.

## Contact
Please contact Kijin Nam <knam@water.ca.gov> for questions.

