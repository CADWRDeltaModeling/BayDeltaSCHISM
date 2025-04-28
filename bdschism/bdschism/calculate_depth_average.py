"""Calculate depth avearged values for later use.

Calculate depth-averaged values from SCHISM NetCDF output files.
Outputs will be in one NetCDF covering the whole processed period.

Usage
-----
$ python calculate_depth_average.py --path_study /path/to/study
--varname salinity --date_base 2017-01-01 --date_start 2017-03-15
--data_end 2017-03-20

NOTE: # Create a new environment named suxarray

conda create -n suxarray -y -c conda-forge python=3.11 pandas xarray dask netcdf4 h5netcdf numba scipy scikit-learn matplotlib pyarrow requests spatialpandas cartopy datashader antimeridian shapely geoviews pyogrio

conda activate suxarray

# Clone and install uxarray/suxarray at the current location

git clone -b suxarray https://github.com/kjnam/uxarray.git &&
pushd uxarray &&
pip install --no-deps -e . &&
popd

git clone -b v2024.09.0 https://github.com/cadwrdeltamodeling/suxarray &&
cd suxarray &&
pip install --no-deps -e . &&
popd
"""

# Standard library imports
import os
from pathlib import Path
import logging

# Third-party library imports
import click
import xarray as xr
import suxarray as sx
import numpy as np
import pandas as pd
from dask.diagnostics import ProgressBar

# Local application/library imports
import schimpy.param as parms


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
ProgressBar().register()


def params(sim_dir):
    fname = os.path.join(sim_dir, "param.nml")
    return parms.read_params(fname)


@click.command(
    help=(
        "Calculate depth-averaged values from SCHISM NetCDF output files.\n"
        "The output is a daily- and depth- averaged NetCDF file.\n\n"
        "Arguments:\n"
        "  nc_file: Path to the NetCDF file to process.(ex: salinity_1.nc)\n"
    )
)
@click.argument("nc_file", type=click.Path(exists=True))
@click.option(
    "--path_study",
    type=click.Path(exists=True),
    default=None,  # Default is None, will compute dynamically
    help="Path to the study directory",
)
@click.option(
    "--out_dir",
    type=click.Path(exists=True),
    default=None,  # Default is None, will compute dynamically
    help="Output directory for the depth-averaged file",
)
@click.help_option("-h", "--help")
def calc_da_cli_single(nc_file, path_study, out_dir):
    """Command line interface for calculating depth average."""
    # Dynamically compute path_study if not provided
    if path_study is None:
        path_study = Path(
            nc_file
        ).parent.parent  # Parent of the parent folder (if sim_dir/outputs/salinity_1.nc, the path_study=sim_dir)
    if out_dir is None:
        out_dir = Path(
            nc_file
        ).parent  # Parent folder (if sim_dir/outputs/salinity_1.nc, the out_dir=sim_dir/outputs)

    calc_daily_depth_average(nc_file, path_study, out_dir)


def calculate_depth_average_single(nc_file, path_study, out_dir, chunks={"time": 2}):
    logger = logging.getLogger()
    logger.info("Starting to calculate depth averaged values...")

    # Set path information
    path_study = Path(path_study)
    date_base = params(path_study).run_start.to_pydatetime()
    filename = os.path.basename(
        nc_file
    )  # Extracts 'varname_fnumber.nc' ex: salinity_1.nc
    varname = os.path.basename(nc_file).split("_")[
        0
    ]  # Extracts the variable name, ex: salinity from salinity_1.nc
    fnumber = filename.split("_")[1].split(".")[
        0
    ]  # Extracts the filenumber, ex: 1 from salinity_1.nc

    logger.info("Reading NetCDF files...")
    path_out2d = os.path.join(path_study, f"outputs/out2d_{fnumber}.nc")
    path_zcoord = os.path.join(path_study, f"outputs/zCoordinates_{fnumber}.nc")
    path_var = os.path.join(path_study, f"outputs/{varname}_{fnumber}.nc")

    # Create a grid object
    grid = sx.open_grid(path_out2d, path_zcoord, chunks=chunks)

    ds_out = xr.open_dataset(nc_file, chunks=chunks)

    # Create a dataset for the variable
    sx_ds = sx.read_schism_nc(
        grid,
        ds_out,
    )

    logger.info(f"Calculating depth-averaged {varname}...")
    # Depth average the variable
    da_var = sx_ds[f"{varname}"].depth_average()

    # add 8 hours to timestamps there's an 8-hr shift issue from xarray converting to UTC.
    # SCHISM has time information attached so xarray shifts by 8 hours
    da_var = da_var.assign_coords(time=da_var["time"])
    da_var["time"] = da_var.time + pd.to_timedelta(8, "h")

    # Daily average the variable
    dda_var_mean = da_var.resample(time="1D", closed="right").mean()

    path_depth_averaged_var = os.path.join(
        path_study, f"outputs/depth_averaged_{varname}_{fnumber}.nc"
    )

    if "units" in sx_ds[f"{varname}"].attrs:
        dda_var_mean.attrs["units"] = sx_ds[f"{varname}"].attrs["units"]

    dda_var_mean.attrs["long_name"] = f"depth-averaged daily {varname}"

    # Write out depth-averaged daily variable to NetCDF
    encoding = {f"{dda_var_mean.name}": {"dtype": "float32"}}
    dda_var_mean.to_dataset().to_netcdf(path_depth_averaged_var, encoding=encoding)
    print(f"\n\tDepth-averaged {varname} saved to:\n\t\t {path_depth_averaged_var}\n")

    logger.info("Calculating depth averaged values at face.")
    # Integrate node values to each element
    dda_var_mean_at_face = dda_var_mean.integrate()
    path_depth_averaged_var_at_face = os.path.join(
        path_study, f"depth_averaged_{varname}_at_face.nc"
    )

    # Write out depth-averaged daily variable to NetCDF
    encoding = {f"{dda_var_mean_at_face.name}": {"dtype": "float32"}}
    dda_var_mean_at_face.to_dataset().to_netcdf(
        path_depth_averaged_var_at_face, encoding=encoding
    )
    print(
        f"\n\tDepth-averaged {varname} at faces saved to:\n\t\t {path_depth_averaged_var_at_face}\n"
    )

    logger.info("Finished calculating depth averaged values.")


# @click.command()
# @click.option(
#     "--varname",
#     type=click.STRING,
#     help="Variable name to calculate depth average in the file name",
# )
# @click.option(
#     "--path_study",
#     type=click.Path(exists=True),
#     default=".",
#     help="Path to the study directory",
# )
# @click.option("--date_base", type=click.DateTime(), help="Base date of the study")
# @click.option("--date_start", type=click.DateTime(), help="Start date to process")
# @click.option("--date_end", type=click.DateTime(), help="end date to process")
# def calc_da_cli_ts(varname, path_study, date_base, date_start, date_end):
#     calculate_depth_average(varname, path_study, date_base, date_start, date_end)

# def calculate_depth_average(varname, path_study, date_base, date_start, date_end):
#     logger = logging.getLogger()
#     logger.info("Starting to calculate depth averaged values...")

#     # Set path information
#     path_study = Path(path_study)
#     day_start = (date_start - date_base).days + 1
#     day_end = (date_end - date_base).days + 1

#     output_items = {
#         "out2d": "outputs/out2d_{}.nc",
#         "zcoord": "outputs/zCoordinates_{}.nc",
#         f"{varname}": "outputs/{}_{{}}.nc".format(varname),
#     }
#     # TODO: Make this configurable
#     chunks = {"time": 2}
#     list_nc_paths = {
#         k: [v.format(i) for i in range(day_start, day_end + 1)]
#         for k, v in output_items.items()
#     }

#     logger.info("Reading NetCDF files...")
#     list_ds = []
#     for _, v in list_nc_paths.items():
#         list_paths = [str(path_study / v[i]) for i in range(len(v))]
#         ds = suxarray.helper.read_schism_nc(list_paths, chunks=chunks)
#         list_ds.append(ds)

#     ds = xr.merge(list_ds)
#     if sx.get_topology_variable(ds) is None:
#         ds = sx.add_topology_variable(ds)
#     ds = sx.coerce_mesh_name(ds)

#     sx_ds = sx.Dataset(ds, sxgrid=sx.Grid(ds))

#     path_depth_averaged_var = f"depth_averaged_{varname}.nc"
#     logger.info(f"Calculating depth-averaged {varname}...")
#     # TODO Move these into suxarray
#     da_depth_averaged_var = sx_ds.depth_average(varname)
#     da_depth_averaged_var.name = f"depth_averaged_{varname}"
#     if "units" in sx_ds[f"{varname}"].attrs:
#         da_depth_averaged_var.attrs["units"] = sx_ds[f"{varname}"].attrs["units"]
#     da_depth_averaged_var.attrs["long_name"] = f"depth-averaged {varname}"

#     encoding = {f"{da_depth_averaged_var.name}": {"dtype": "float32"}}
#     da_depth_averaged_var.to_dataset().to_netcdf(
#         path_depth_averaged_var, encoding=encoding
#     )

#     chunks = {"time": 48 * 8}
#     da_depth_averaged_var = xr.open_dataset(path_depth_averaged_var, chunks=chunks)[
#         f"depth_averaged_{varname}"
#     ]
#     logger.info("Calculating depth averaged values at face.")
#     da_depth_averaged_var_at_face = sx_ds.face_average(da_depth_averaged_var)
#     da_depth_averaged_var_at_face.name = f"depth_averaged_{varname}_at_face"
#     encoding = {f"{da_depth_averaged_var_at_face.name}": {"dtype": "float32"}}
#     path_depth_averaged_var_at_face = f"depth_averaged_{varname}_at_face.nc"
#     da_depth_averaged_var_at_face.to_dataset().to_netcdf(
#         path_depth_averaged_var_at_face, encoding=encoding
#     )

#     logger.info("Finished calculating depth averaged values.")


if __name__ == "__main__":
    # calculate_depth_average()
    calculate_depth_average_single(
        "/scratch/projects/summer_x2_2025/simulations/2016_noaction/outputs/salinity_1.nc",
        "/scratch/projects/summer_x2_2025/simulations/2016_noaction",
        "/scratch/projects/summer_x2_2025/simulations/2016_noaction/outputs",
    )
