"""
"""

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
    argparser.add_argument("--path_hsi", type=lambda s: Path(s))
    argparser.add_argument(
        "--path_out_nc", default="hsi_area.nc", type=lambda s: Path(s)
    )
    argparser.add_argument(
        "--path_out_csv", default="hsi_area.csv", type=lambda s: Path(s)
    )
    return argparser


def main():
    argparser = create_argparser()
    args = argparser.parse_args()

    path_out2d = args.path_out2d
    path_common = args.path_common
    path_hsi = args.path_hsi
    path_out_csv = args.path_out_csv
    path_out_nc = args.path_out_nc

    ds_out2d = suxarray.helper.read_schism_nc(path_out2d)
    if sx.get_topology_variable(ds_out2d) is None:
        ds_out2d = sx.add_topology_variable(ds_out2d)
    ds_out2d = sx.coerce_mesh_name(ds_out2d)

    logging.info("Creating a grid object...")
    sx_ds = sx.Dataset(ds_out2d, sxgrid=sx.Grid(ds_out2d))

    logging.info("Calculating face areas...")
    da_face_areas = sx_ds.sxgrid.compute_face_areas()
    da_face_areas.name = "face_area"
    da_face_areas.attrs["units"] = "m2"
    da_face_areas.attrs["long_name"] = "Face area"

    logging.info("Reading habitat Suitablity Indices...")
    chunks = {"time": 48}
    ds_hsi = xr.open_dataset(path_hsi, chunks=chunks)
    da_hsi = ds_hsi["hsi"].fillna(0.0)

    path_subregions_nc = path_common / "subregion_hsi.nc"
    ds_subregions = xr.open_dataset(path_subregions_nc)
    # ds_subregions = xr.decode_cf(ds_subregions)
    # ds_subregions = ds_subregions.rename({"nSCHISM_hgrid_face": "nMesh2_face"})

    # path_region_points = path_common / "region_pointsUTM.csv"
    # df_region_points = pd.read_csv(path_region_points, header=0)
    # list_regions = df_region_points["SUBREGION"].unique()
    list_regions = list(ds_subregions.keys())

    list_areas_hsi = []
    list_total_areas = []
    for region in list_regions:
        da_elem_idx = ds_subregions[region]
        da_face_areas_in_region = da_face_areas.where(da_elem_idx, drop=True)
        da_area_hsi = xr.dot(
            da_face_areas_in_region,
            da_hsi.where(da_elem_idx, drop=True),
            dims="nMesh2_face",
        )
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

    ds_area_hsi.to_netcdf(path_out_nc)
    ds_area_hsi.to_dataframe().to_csv(path_out_csv)

    logging.info("Done...")


if __name__ == "__main__":
    main()
