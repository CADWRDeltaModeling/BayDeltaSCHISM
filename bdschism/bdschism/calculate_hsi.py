""" Calculate HSI from SCHISM outputs

It is based on the previous script `hsi_Bever_updated.py`.

NOTE: Use the master branch of suxarray as of 2023-06-30
and uxarray v2023.06.
"""
from pathlib import Path
import logging
import glob
import re
import click
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


@click.command()
@click.option(
    "--path_study",
    type=click.Path(exists=True),
    required=True,
    help="Path to the study directory",
)
@click.option(
    "--path_input",
    type=click.Path(exists=True),
    required=True,
    help="Path to other inputs",
)
@click.option("--do_depthaverage", type=bool, default=False)
def main(path_study, path_input, do_depthaverage):
    logger = logging.getLogger()
    logger.info("Starting HSI calculation...")

    # Set path information
    path_study = Path(path_study)
    path_input = Path(path_input)
    day_start = 75
    day_end = 223
    # day_end = 77

    output_items = {
        "out2d": "outputs/out2d_{}.nc",
        "zcoord": "outputs/zCoordinates_{}.nc",
        "salinity": "outputs/salinity_{}.nc",
        "hvel_x": "outputs/horizontalVelX_{}.nc",
        "hvel_y": "outputs/horizontalVelY_{}.nc",
    }
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

    # grid = sx.Grid(ds)
    sx_ds = sx.Dataset(ds, sxgrid=sx.Grid(ds))

    # Chunking for parallel processing
    # Rule of thumb is about 100MB per chunk.
    # grid.ds = grid.ds.chunk({"time": 2})

    path_depth_averaged_salinity = "depth_averaged_salinity.nc"
    path_depth_averaged_hvel_x = "depth_averaged_hvel_x.nc"
    path_depth_averaged_hvel_y = "depth_averaged_hvel_y.nc"
    if do_depthaverage:
        logger.info("Calculating depth-averaged salinity...")
        # TODO Move these into suxarray
        da_depth_averaged_salinity = sx_ds.depth_average("salinity")
        da_depth_averaged_salinity.name = "depth_averaged_salinity"
        da_depth_averaged_salinity.attrs["units"] = "psu"
        da_depth_averaged_salinity.attrs["long_name"] = "depth-averaged salinity"

        (
            da_depth_averaged_salinity.to_dataset().to_netcdf(
                path_depth_averaged_salinity
            )
        )

        logger.info("Calculating depth-averaged hvel x...")
        da_depth_averaged_hvel_x = sx_ds.depth_average("horizontalVelX")
        da_depth_averaged_hvel_x.name = "depth_averaged_hvel_x"
        da_depth_averaged_hvel_x.attrs["units"] = "m2 s-1"
        da_depth_averaged_hvel_x.attrs[
            "long_name"
        ] = "depth-averaged horizontal velocity in x direction"

        (da_depth_averaged_hvel_x.to_dataset().to_netcdf(path_depth_averaged_hvel_x))

        logger.info("Calculating depth-averaged hvel y...")
        da_depth_averaged_hvel_y = sx_ds.depth_average("horizontalVelY")
        da_depth_averaged_hvel_y.name = "depth_averaged_hvel_y"
        da_depth_averaged_hvel_y.attrs["units"] = "m2 s-1"
        da_depth_averaged_hvel_y.attrs[
            "long_name"
        ] = "depth-averaged horizontal velocity in y direction"

        (da_depth_averaged_hvel_y.to_dataset().to_netcdf(path_depth_averaged_hvel_y))

    logger.info(
        "Skipping depth-averaged salinity calculation. " " Instead, read from files"
    )
    ds_depth_averaged_salinity = xr.open_dataset(
        path_depth_averaged_salinity, chunks=chunks
    )
    da_depth_averaged_salinity = ds_depth_averaged_salinity.depth_averaged_salinity
    ds_depth_averaged_hvel_x = xr.open_dataset(
        path_depth_averaged_hvel_x, chunks=chunks
    )
    da_depth_averaged_hvel_x = ds_depth_averaged_hvel_x.depth_averaged_hvel_x
    ds_depth_averaged_hvel_y = xr.open_dataset(
        path_depth_averaged_hvel_y, chunks=chunks
    )
    da_depth_averaged_hvel_y = ds_depth_averaged_hvel_y.depth_averaged_hvel_y

    logger.info("Calculating depth-averaged horizontal velocity magnitude...")
    da_depth_averaged_hvel_mag = (
        xr.apply_ufunc(
            lambda v_x, v_y: np.hypot(v_x, v_y),
            da_depth_averaged_hvel_x,
            da_depth_averaged_hvel_y,
            dask="parallelized",
        )
        .chunk({"time": 2})
        .persist()
    )
    da_depth_averaged_hvel_mag_daily_max = (
        da_depth_averaged_hvel_mag.resample(time="1D", origin="start").max().persist()
    )
    da_depth_averaged_hvel_mag_daily_max = shift_30min_up(
        da_depth_averaged_hvel_mag_daily_max
    )
    da_depth_averaged_hvel_mag_daily_max.name = "depth_averaged_hvel_mag_daily_max"
    da_depth_averaged_hvel_mag_daily_max.attrs["units"] = "m s-1"

    da_depth_averaged_hvel_mag_daily_max_at_face = sx_ds.face_average(
        da_depth_averaged_hvel_mag_daily_max
    )
    da_depth_averaged_hvel_mag_daily_max_at_face = (
        da_depth_averaged_hvel_mag_daily_max_at_face.assign_coords(
            nMesh2_face=np.arange(sx_ds.sxgrid.nMesh2_face)
        )
    )

    da_daily_salinity_fraction_under_6 = (
        xr.where(da_depth_averaged_salinity < 6.0, 1, 0)
        .resample(time="1D", origin="start")
        .mean()
        .persist()
    )
    da_daily_salinity_fraction_under_6 = shift_30min_up(
        da_daily_salinity_fraction_under_6
    )
    da_salinity_fraction_under_6_at_face = sx_ds.face_average(
        da_daily_salinity_fraction_under_6
    )

    logger.info("Map grids...")
    path_coarse = path_input / "bay_delta_coarse_v4.gr3"
    path_fine = path_study / "hgrid.gr3"
    path_map = "grid_mapping_and_weight.nc"
    map_grids(path_coarse, path_fine, path_map)

    logger.info("Read temperature and turbidity quantile data...")

    ds_grid_mapping = xr.open_dataset(path_map, mask_and_scale=False)

    path_temperature_csv = path_input / "temperature_*.csv"
    da_temperature_quantile = read_quantile_data(path_temperature_csv)

    da_temperature_quantile = (
        da_temperature_quantile.isel(
            nMesh2_node=ds_grid_mapping.map_to_coarse_nodes
        )
        * ds_grid_mapping.weight
    ).sum(dim="three") / ds_grid_mapping.weight.sum(dim="three")
    da_temperature_quantile_at_face = sx_ds.face_average(da_temperature_quantile)
    da_temperature_quantile_at_face.name = "temperature_quantile"
    da_temperature_quantile_at_face.attrs["units"] = "degC"
    n_periods = da_temperature_quantile.time.size
    timestamps = pd.date_range(start="2017-07-01", freq="1D", periods=n_periods)
    da_temperature_quantile_at_face = da_temperature_quantile_at_face.assign_coords(
        time=timestamps
    )

    path_turbidity_csv = path_input / "ln_turbidity_*.csv"
    da_turbidity_quantile = read_quantile_data(path_turbidity_csv)
    da_turbidity_quantile = xr.apply_ufunc(np.exp, da_turbidity_quantile)
    da_turbidity_quantile = (
        da_turbidity_quantile.isel(
            nMesh2_node=ds_grid_mapping.map_to_coarse_nodes
        )
        * ds_grid_mapping.weight
    ).sum(dim="three") / ds_grid_mapping.weight.sum(dim="three")
    da_turbidity_quantile_at_face = sx_ds.face_average(da_turbidity_quantile)
    da_turbidity_quantile_at_face.name = "turbidity_quantile"
    da_turbidity_quantile_at_face.attrs["units"] = "degC"
    n_periods = da_turbidity_quantile.time.size
    timestamps = pd.date_range(start="2017-07-01", freq="1D", periods=n_periods)
    da_turbidity_quantile_at_face = da_turbidity_quantile_at_face.assign_coords(
        time=timestamps
    )

    logger.info("Calculating indices...")
    da_temperature_levels = xr.where(da_temperature_quantile_at_face < 24.0, 1, 0).sum(
        dim="quantile"
    )
    da_si_temperature = xr.apply_ufunc(
        lambda v: np.array([0, 0.25, 0.5, 0.75, 1.0])[v],
        da_temperature_levels,
        dask="parallelized",
    )
    da_turbidity_levels = xr.where(da_turbidity_quantile_at_face > 12.0, 1, 0).sum(
        dim="quantile"
    )
    da_si_turbidity = xr.apply_ufunc(
        lambda v: np.array([0, 0.25, 0.5, 0.75, 1.0])[v],
        da_turbidity_levels,
        dask="parallelized",
    )

    bins = [0.5, 0.71, 0.82, 0.89, 1.02, 1.1]

    fns = [
        lambda v: 1.0,
        lambda v: -0.4655 * v + 1.233,
        lambda v: -1.8608 * v + 2.228,
        lambda v: -3.0193 * v + 3.179,
        lambda v: -1.5059 * v + 1.836,
        lambda v: -2.4432 * v + 2.792,
        lambda v: -0.0859 * v + 0.194,
    ]
    da_hvel_factors = xr.apply_ufunc(
        lambda v: np.clip(bin_and_apply(v, bins, fns), 0.0, 1.0),
        da_depth_averaged_hvel_mag_daily_max_at_face,
        dask="parallelized",
    )
    da_hvel_factors.name = "SI_hvel"
    da_hvel_factors.attrs["units"] = "dimensionless"
    da_hvel_factors.attrs["long_name"] = "Suitability Index based on depth-averaged horizontal velocity magnitude"
    path_si_hvel = "si_hvel.nc"
    da_hvel_factors.to_dataset().to_netcdf(path_si_hvel)

    bins = [0.195, 0.448, 0.723, 0.802, 0.839, 0.949]

    fns = [
        lambda v: 0.1537 * v + 0.069,
        lambda v: 0.7937 * v - 0.055,
        lambda v: 0.7273 * v - 0.025,
        lambda v: 2.5386 * v - 1.334,
        lambda v: 5.3637 * v - 3.600,
        lambda v: 0.8902 * v + 0.155,
        lambda v: 1.0,
    ]

    da_salinity_factors = xr.apply_ufunc(
        lambda v: bin_and_apply(v, bins, fns),
        da_salinity_fraction_under_6_at_face,
        dask="parallelized",
    )
    da_salinity_factors.name = "SI_salinity"
    da_salinity_factors.attrs["units"] = "dimensionless"
    da_salinity_factors.attrs["long_name"] = "Suitability Index based on depth-averaged salinity"
    path_si_salinity = "si_salinity.nc"
    da_salinity_factors.to_dataset().to_netcdf(path_si_salinity)

    logger.info("Calculating HSI...")
    da_hsi = (
        0.67 * da_salinity_fraction_under_6_at_face
        + 0.33 * da_depth_averaged_hvel_mag_daily_max_at_face
    )

    chunks = {"time": 2}
    logger.info("Calculating turbidity cutoff probability...")
    da_probability = xr.apply_ufunc(
        interpolate_turbidity_cutoff_probability,
        da_turbidity_quantile_at_face.chunk(chunks),
        da_turbidity_levels.chunk(chunks),
        input_core_dims=[
            [
                "quantile",
            ],
            [],
        ],
        output_dtypes=float,
        dask="parallelized",
    )

    da_hsi_final = (1.0 - 0.6 * da_probability) * da_hsi * da_si_temperature
    da_hsi_final.name = "hsi"
    da_hsi_final.attrs["units"] = "dimensionless"
    da_hsi_final.attrs["long_name"] = "Habitat Suitability Index"
    path_hsi = "hsi.nc"
    da_hsi_final.to_dataset().to_netcdf(path_hsi)

    path_subregions_nc = path_input / "subregion_hsi.nc"
    ds_subregions = xr.open_dataset(path_subregions_nc)
    ds_subregions.time.attrs["units"] = "seconds since 2017-04-18 00:00:00"
    ds_subregions = xr.decode_cf(ds_subregions)
    ds_subregions = ds_subregions.rename({"nSCHISM_hgrid_face": "nMesh2_face"})
    path_region_points = path_input / "region_pointsUTM.csv"
    df_region_points = pd.read_csv(path_region_points, header=0)
    list_regions = df_region_points["SUBREGION"].unique()

    da_face_areas = sx_ds.sxgrid.compute_face_areas()
    # da_face_areas = da_face_areas.rename({"nMesh2_face": "nMesh2_face"})

    logger.info("Calculating HSI areas for each region...")
    list_areas_hsi = []
    list_total_areas = []
    for region in list_regions:
        print(f"Processing {region}")
        da_elem_idx = ds_subregions[region]
        da_face_areas_in_region = da_face_areas.where(da_elem_idx, drop=True)
        da_area_hsi = xr.dot(
            da_face_areas_in_region,
            da_hsi_final.where(da_elem_idx, drop=True),
            dims="nMesh2_face",
        ).chunk({"time": 2})
        list_areas_hsi.append(da_area_hsi)
        total_region_area = da_face_areas_in_region.sum()
        list_total_areas.append(total_region_area)
    da_area_hsi_all = xr.concat(list_areas_hsi, pd.Index(list_regions, name="region"))
    da_area_hsi_all.name = "hsi_area"
    da_area_hsi_all.attrs["units"] = "m2"
    da_area_hsi_all.attrs["long_name"] = "HSI area for each region"
    ds_area_hsi = da_area_hsi_all.to_dataset()

    da_subareas = xr.concat(list_total_areas, pd.Index(list_regions, name="region"))
    da_subareas.name = "subarea"
    da_subareas.attrs["units"] = "m2"
    ds_area_hsi = ds_area_hsi.update({"subarea": da_subareas})

    path_hsi_area = "hsi_area.nc"
    logger.info("Calculating and writing HSI areas to a NetCDF file...")
    ds_area_hsi.to_netcdf(path_hsi_area)

    logger.info("Done.")


def shift_30min_up(da):
    """Shift time coordinate 30 minutes up"""
    return da.assign_coords(time=da.coords["time"] - pd.to_timedelta("30m"))


def interpolate_turbidity_cutoff_probability(turb, levels):
    """Interpolate turbidity probability at 12 NTU from turbidity quantile data"""
    probability_all = np.zeros_like(turb)
    # The last dimension through apply_ufnuc is the quantile dimension
    funclist = [
        lambda v1, v2: (12.0 - v1) / (v2 - v1) * 0.20 + 0.05,
        lambda v1, v2: (12.0 - v1) / (v2 - v1) * 0.25 + 0.25,
        lambda v1, v2: (12.0 - v1) / (v2 - v1) * 0.25 + 0.5,
        lambda v1, v2: (12.0 - v2) / (v2 - v1) * 0.25 + 0.75,
    ]
    n_quantiles = turb.shape[-1]
    for l in range(n_quantiles):
        # For the last quantile, use the previous quantile set
        l_ = l if l != n_quantiles - 1 else l - 1
        v1 = turb[..., l_]
        v2 = turb[..., l_ + 1]
        probability_all[..., l] = funclist[l](v1, v2)
    result = np.select(
        [levels == i for i in range(n_quantiles)],
        [probability_all[..., i] for i in range(n_quantiles)],
        default=0.0,
    )
    np.clip(result, 0.0, 1.0, out=result)
    return result


def bin_and_apply(val, bins, fns):
    digitized = np.digitize(val, bins)
    # result = digitized
    result = np.empty_like(val)
    for i in range(len(fns)):
        mask = np.where(digitized == i)
        result[mask] = fns[i](val[mask])
    np.clip(result, 0.0, 1.0, out=result)
    return result


def read_quantile_data(path_csv_pattern):
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
        np.stack([df.values for df in dfs]),
        dims=["quantile", "time", "nMesh2_node"],
        coords={"quantile": quantiles},
    )
    return da_result


def map_grids(coarse_path, fine_path, map_path):
    # Read coarse grid
    coarse_grid = sx.read_hgrid_gr3(coarse_path)

    # Read fine grid
    fine_grid = sx.read_hgrid_gr3(fine_path)

    fine_nodes = fine_grid.node_points

    coarse_face_id_from_fine_node = coarse_grid.elem_strtree.query(
        fine_nodes, predicate="intersects"
    )
    coarse_face_nodes = coarse_grid.Mesh2_face_nodes.values
    # Create an empty array to store the node mapping. `-1` is the fill value.
    map_to_coarse_nodes = np.full((fine_grid.nMesh2_node, 3), -1, dtype=int)

    map_to_coarse_nodes[coarse_face_id_from_fine_node[0], :] = coarse_face_nodes[
        coarse_face_id_from_fine_node[1]
    ][:, :3]
    fine_nodes_not_found = list(
        set(range(fine_grid.nMesh2_node)) - set(coarse_face_id_from_fine_node[0])
    )

    if len(fine_nodes_not_found) > 0:
        fine_nodes_not_found.sort()
        coarse_nodes_nearest = xr.apply_ufunc(
            lambda p: coarse_grid.node_strtree.nearest(p),
            fine_nodes.isel(nMesh2_node=fine_nodes_not_found),
            vectorize=True,
            dask="parallelized",
        )
        map_to_coarse_nodes[fine_nodes_not_found, 0] = coarse_nodes_nearest

    da_map_to_coarse_nodes = xr.DataArray(
        map_to_coarse_nodes,
        dims=("nMesh2_node", "three"),
        attrs={"_FillValue": -1, "start_index": 0},
        name="map_to_coarse_nodes",
    )

    def _calculate_weight(conn, points):
        """Calculate distance between a point and a set of points."""
        x = coarse_grid.Mesh2_node_x.values[conn]
        y = coarse_grid.Mesh2_node_y.values[conn]
        xy = np.array([p.xy for p in points])
        dist = np.apply_along_axis(np.linalg.norm, 1, np.stack((x, y), axis=1) - xy)
        weight = np.reciprocal(dist)
        # Find where we see the infinite values
        mask = np.where(np.isinf(weight))
        # Adjust the weights for the node
        weight[mask[0], :] = 0.0
        weight[mask] = 1.0
        # weight /= weight.sum(axis=1).reshape(-1, 1)
        return weight

    chunk_size = None
    da_weight = xr.apply_ufunc(
        _calculate_weight,
        da_map_to_coarse_nodes.chunk({"nMesh2_node": chunk_size}),
        fine_nodes.chunk({"nMesh2_node": chunk_size}),
        input_core_dims=[["three"], []],
        output_core_dims=[["three"]],
        dask="parallelized",
        output_dtypes=float,
    ).persist()

    # Create a dataset and save it
    ds_map_and_weight = da_map_to_coarse_nodes.to_dataset(
        name=da_map_to_coarse_nodes.name
    )
    ds_map_and_weight["weight"] = da_weight
    path_map_and_weight = map_path
    ds_map_and_weight.to_netcdf(path_map_and_weight)


if __name__ == "__main__":
    main()
