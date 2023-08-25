""" Calculate depth avearged values for later use.

Calculate depth-averaged values from SCHISM NetCDF output files.
Outputs will be in one NetCDF covering the whole processed period.

Usage
-----
$ python calculate_depth_average.py --path_study /path/to/study
--varname salinity --date_base 2017-01-01 --date_start 2017-03-15
--data_end 2017-03-20

NOTE: Use the master branch of suxarray as of 2023-06-30
and uxarray v2023.06.
"""
from pathlib import Path
import logging
import click
import xarray as xr
import suxarray as sx
import suxarray.helper
from dask.diagnostics import ProgressBar


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
ProgressBar().register()


@click.command()
@click.option(
    "--varname",
    type=click.STRING,
    help="Variable name to calculate depth average in the file name",
)
@click.option(
    "--path_study",
    type=click.Path(exists=True),
    default=".",
    help="Path to the study directory",
)
@click.option("--date_base", type=click.DateTime(), help="Base date of the study")
@click.option("--date_start", type=click.DateTime(), help="Start date to process")
@click.option("--date_end", type=click.DateTime(), help="end date to process")
def calculate_depth_average(varname, path_study, date_base, date_start, date_end):
    logger = logging.getLogger()
    logger.info("Starting to calculate depth averaged values...")

    # Set path information
    path_study = Path(path_study)
    day_start = (date_start - date_base).days + 1
    day_end = (date_end - date_base).days + 1

    output_items = {
        "out2d": "outputs/out2d_{}.nc",
        "zcoord": "outputs/zCoordinates_{}.nc",
        f"{varname}": "outputs/{}_{{}}.nc".format(varname),
    }
    # TODO: Make this configurable
    chunks = {"time": 2}
    list_nc_paths = {
        k: [v.format(i) for i in range(day_start, day_end + 1)]
        for k, v in output_items.items()
    }

    logger.info("Reading NetCDF files...")
    list_ds = []
    for _, v in list_nc_paths.items():
        list_paths = [str(path_study / v[i]) for i in range(len(v))]
        ds = suxarray.helper.read_schism_nc(list_paths, chunks=chunks)
        list_ds.append(ds)

    ds = xr.merge(list_ds)
    if sx.get_topology_variable(ds) is None:
        ds = sx.add_topology_variable(ds)
    ds = sx.coerce_mesh_name(ds)

    sx_ds = sx.Dataset(ds, sxgrid=sx.Grid(ds))

    path_depth_averaged_var = f"depth_averaged_{varname}.nc"
    logger.info(f"Calculating depth-averaged {varname}...")
    # TODO Move these into suxarray
    da_depth_averaged_var = sx_ds.depth_average(varname)
    da_depth_averaged_var.name = f"depth_averaged_{varname}"
    if "units" in sx_ds[f"{varname}"].attrs:
        da_depth_averaged_var.attrs["units"] = sx_ds[f"{varname}"].attrs["units"]
    da_depth_averaged_var.attrs["long_name"] = f"depth-averaged {varname}"

    encoding = {f"{da_depth_averaged_var.name}": {"dtype": "float32"}}
    da_depth_averaged_var.to_dataset().to_netcdf(
        path_depth_averaged_var, encoding=encoding
    )

    chunks = {"time": 48 * 8}
    da_depth_averaged_var = xr.open_dataset(path_depth_averaged_var, chunks=chunks)[
        f"depth_averaged_{varname}"
    ]
    logger.info("Calculating depth averaged values at face.")
    da_depth_averaged_var_at_face = sx_ds.face_average(da_depth_averaged_var)
    da_depth_averaged_var_at_face.name = f"depth_averaged_{varname}_at_face"
    encoding = {f"{da_depth_averaged_var_at_face.name}": {"dtype": "float32"}}
    path_depth_averaged_var_at_face = f"depth_averaged_{varname}_at_face.nc"
    da_depth_averaged_var_at_face.to_dataset().to_netcdf(
        path_depth_averaged_var_at_face, encoding=encoding
    )

    logger.info("Finished calculating depth averaged values.")


if __name__ == "__main__":
    calculate_depth_average()
