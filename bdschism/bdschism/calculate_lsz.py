from pathlib import Path
import logging
import argparse
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
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--path_out2d", type=lambda s: Path(s))
    argparser.add_argument("--path_common", type=lambda s: Path(s))
    argparser.add_argument("--path_salinity_nc", type=lambda s: Path(s))
    return argparser


def main():
    """Calculate LSZ less than 6.0 and 7.0"""
    # Create an argument parser
    argparser = create_argparser()
    args = argparser.parse_args()

    path_out2d = args.path_out2d
    path_common = args.path_common
    path_salinity_nc = args.path_salinity_nc

    # Read just one out2d file to get the mesh information
    ds_out2d = suxarray.helper.read_schism_nc(path_out2d)
    if sx.get_topology_variable(ds_out2d) is None:
        ds_out2d = sx.add_topology_variable(ds_out2d)
    ds_out2d = sx.coerce_mesh_name(ds_out2d)

    logging.info("Creating a grid object...")
    sx_ds = sx.Dataset(ds_out2d, sxgrid=sx.Grid(ds_out2d))
    da_face_areas = sx_ds.sxgrid.compute_face_areas()

    # Read processed depth-average salinity at face
    logging.info("Reading postprocessed depth-averaged data...")
    # The chunk size can be optimized depending on the available memory
    chunks = {"time": 48}
    ds_salinity = xr.open_dataset(path_salinity_nc, chunks=chunks)
    da_depth_averaged_salinity_at_face = ds_salinity["depth_averaged_salinity_at_face"]

    logging.info("Reading subregion data...")
    path_subregions_nc = path_common / "subregion_hsi.nc"
    ds_subregions = xr.open_dataset(path_subregions_nc)
    list_regions = list(ds_subregions.keys())

    # Calculate LSZ less than 6.0 and 7.0
    # NOTE These thresholds are hard-coded for now.
    # The loop can be factored out.
    thresholds = [6.0, 7.0]
    for threshold in thresholds:
        logging.info(f"Calculating LSZ less than {threshold}...")
        da_salinity_less_than_threshold = xr.where(
            da_depth_averaged_salinity_at_face < threshold, 1.0, 0.0
        )
        da_salinity_less_than_threshold_daily = (
            da_salinity_less_than_threshold.resample(time="1D", origin="start").mean()
        )
        da_salinity_less_than_threshold_daily = shift_30min_up(
            da_salinity_less_than_threshold_daily
        )
        da_lsz_total_threshold = da_salinity_less_than_threshold_daily.dot(
            da_face_areas
        ).persist()
        da_lsz_total_threshold.name = f"lsz_less_than_{threshold}"
        da_lsz_total_threshold.attrs["units"] = "m2"

        da_lsz_total_threshold.to_netcdf(f"lsz_less_than_{threshold}.nc")
        da_lsz_total_threshold.to_dataframe().to_csv(f"lsz_less_than_{threshold}.csv")

        logging.info("Calculating LSZ area for each region...")
        list_areas = []
        list_total_areas = []
        for region in list_regions:
            da_elem_idx = ds_subregions[region]
            da_face_areas_in_region = da_face_areas.where(da_elem_idx, drop=True)
            da_area_lsz = xr.dot(
                da_face_areas_in_region,
                da_salinity_less_than_threshold.where(da_elem_idx, drop=True),
                dims="nMesh2_face",
            )
            list_areas.append(da_area_lsz)
            total_region_area = da_face_areas_in_region.sum()
            list_total_areas.append(total_region_area)

        da_area_lsz_all = xr.concat(list_areas, pd.Index(list_regions, name="region"))
        da_area_lsz_all.name = "lsz_area"
        da_area_lsz_all.attrs["units"] = "m2"
        da_area_lsz_all.attrs["long_name"] = (
            f"LSZ area for each region under {threshold}"
        )
        ds_area_lsz = da_area_lsz_all.to_dataset()

        da_subareas = xr.concat(list_total_areas, pd.Index(list_regions, name="region"))
        da_subareas.name = "subarea"
        da_subareas.attrs["units"] = "m2"
        ds_area_lsz = ds_area_lsz.update({"subarea": da_subareas})

        path_out_nc = f"lsz_area_less_than_{threshold}.nc"
        path_out_csv = f"lsz_area_less_than_{threshold}.csv"
        ds_area_lsz.to_netcdf(path_out_nc)
        ds_area_lsz.to_dataframe().to_csv(path_out_csv)

    logging.info("Done")


def shift_30min_up(da):
    """Shift time coordinate 30 minutes up"""
    return da.assign_coords(time=da.coords["time"] - pd.to_timedelta("30m"))


if __name__ == "__main__":
    main()
