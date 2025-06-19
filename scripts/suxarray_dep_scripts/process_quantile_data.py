"""
Process and convert convert quantile data defined at coarse grid nodes to a
fine grid nodes.
"""

from pathlib import Path
import logging
import argparse
import glob
import re
import numpy as np
import pandas as pd
import xarray as xr
import suxarray as sx
import suxarray.helper

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


def create_argparser():
    """Create an argument parser

    Returns
    -------
    argparse.ArgumentParser
    """
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--path_out2d",
        type=lambda s: Path(s),
        help=(
            "Path to one out2d file. This is used to get the mesh information. Any"
            " out2d file will work."
        ),
    )
    argparser.add_argument(
        "--path_mapping", type=lambda s: Path(s), help="Path to the grid mapping data."
    )
    argparser.add_argument(
        "--date_start",
        type=lambda s: pd.to_datetime(s),
        help="start date for the quantile data. Use any year.",
    )
    argparser.add_argument(
        "--path_quantile",
        type=lambda s: Path(s),
        help="Path to quantile data defined at coarse grid nodes.",
    )
    argparser.add_argument(
        "--path_out",
        type=lambda s: Path(s),
        default=".",
        help="Path to the output directory.",
    )
    return argparser


def main():
    # Process command line arguments
    argparser = create_argparser()
    args = argparser.parse_args()

    path_out2d = args.path_out2d
    path_mapping = args.path_mapping
    date_start = args.date_start
    path_quantile = args.path_quantile
    path_out = args.path_out

    # Read the grid information from one out2d and create a grid object
    logging.info("Reading one out2d file to get the mesh information...")
    ds_out2d = suxarray.helper.read_schism_nc(path_out2d)
    if sx.get_topology_variable(ds_out2d) is None:
        ds_out2d = sx.add_topology_variable(ds_out2d)
    ds_out2d = sx.coerce_mesh_name(ds_out2d)

    logging.info("Creating a grid object...")
    sx_ds = sx.Dataset(ds_out2d, sxgrid=sx.Grid(ds_out2d))

    logging.info("Reading the grid mapping data...")
    ds_grid_mapping = xr.open_dataset(path_mapping, mask_and_scale=False)

    logging.info("Reading temperature quantile data...")
    path_temperature_csv = path_quantile / "temperature_*.csv"
    da_temperature_quantile = read_quantile_data(path_temperature_csv)

    logging.info("Processing temperature quantile data...")
    da_temperature_quantile_fine_at_face = process_quantile(
        da_temperature_quantile, date_start, sx_ds, ds_grid_mapping
    )
    path_out_temperature = path_out / "temperature_quantile_at_face.nc"
    da_temperature_quantile_fine_at_face.name = "temperature_quantile_at_face"
    encoding = {f"{da_temperature_quantile_fine_at_face.name}": {"dtype": "float32"}}
    da_temperature_quantile_fine_at_face.to_dataset().to_netcdf(
        path_out_temperature, encoding=encoding
    )

    logging.info("Reading turbidity quantile data...")
    path_turbidity_csv = path_quantile / "ln_turbidity_*.csv"
    da_turbidity_quantile = read_quantile_data(path_turbidity_csv)
    da_turbidity_quantile = xr.apply_ufunc(np.exp, da_turbidity_quantile)

    logging.info("Processing turbidity quantile data...")
    da_turbidity_quantile_fine_at_face = process_quantile(
        da_turbidity_quantile, date_start, sx_ds, ds_grid_mapping
    )
    path_out_turbidity = path_out / "turbidity_quantile_at_face.nc"
    da_turbidity_quantile_fine_at_face.name = "turbidity_quantile_at_face"
    encoding = {f"{da_turbidity_quantile_fine_at_face.name}": {"dtype": "float32"}}
    da_turbidity_quantile_fine_at_face.to_dataset().to_netcdf(
        path_out_turbidity, encoding=encoding
    )

    logging.info("Done...")


def process_quantile(dataarray, date_start, sx_ds, ds_grid_mapping):
    n_periods = dataarray.time.size
    # Use 1900 for the fake year
    timestamps = pd.date_range(start=date_start, freq="1D", periods=n_periods)
    dataarray = dataarray.assign_coords(time=timestamps)
    dataarray.time.attrs["comment"] = (
        "Note: This data is meant from {}. Ignore the year part."
    )

    dataarray_fine = (
        dataarray.isel(nMesh2_node=ds_grid_mapping.map_to_coarse_nodes)
        * ds_grid_mapping.weight
    ).sum(dim="three") / ds_grid_mapping.weight.sum(dim="three")

    dataarray_fine_at_face = sx_ds.face_average(dataarray_fine)
    return dataarray_fine_at_face


def read_quantile_data(path_csv_pattern):
    """Read quantile data from a set of CSV files.

    Parameters
    ----------
    path_csv_pattern : str or Path
        Path pattern to the CSV files to read.

    Returns
    -------
    xr.DataArray
    """
    dfs = []
    quantiles = []
    path_csvs = glob.glob(str(path_csv_pattern))
    for path_file in path_csvs:
        # Get the quantile value from the file name
        quantile = int(re.search(r"\d+", path_file).group(0))
        quantiles.append(quantile)
        df = pd.read_csv(path_file, header=None)
        dfs.append(df)
    da_result = xr.DataArray(
        np.stack([df.iloc[:, 1:].values for df in dfs]),
        dims=["quantile", "time", "nMesh2_node"],
        coords={"quantile": quantiles},
    )
    return da_result


if __name__ == "__main__":
    main()
