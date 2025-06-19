from pathlib import Path
import logging
import yaml
import click
import shapely
import numpy as np
import xarray as xr
from shapely.strtree import STRtree
from shapely.geometry import Polygon
import suxarray as sx
import suxarray.helper

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


@click.command()
@click.argument("out2d", type=click.Path(exists=True))
@click.argument("polygon_yaml", type=click.Path(exists=True))
@click.argument("subregion_nc", type=click.Path())
def create_subregion_nc(out2d, polygon_yaml, subregion_nc):
    """
    Create a netCDF file containing subregion flags.

    Parameters
    ----------
    out2d : str
        Filepath to a SCHISM 2D netCDF file.
    polygon_yaml : str
        Filepath to a YAML file containing a list of polygons.
    subregion_nc : str
        Filepath to a netCDF file to be created.
    """
    logging.info(f"Reading {polygon_yaml}...")
    with open(polygon_yaml, "r") as f:
        yaml_data = yaml.safe_load(f)
        polygons = {}
        for item in yaml_data["polygons"]:
            name = item["name"]
            polygon = Polygon(item["vertices"])
            polygons[name] = polygon

    logging.info(f"Reading {out2d}...")
    ds_out2d = suxarray.helper.read_schism_nc(out2d)
    if sx.get_topology_variable(ds_out2d) is None:
        ds_out2d = sx.add_topology_variable(ds_out2d)
    ds_out2d = sx.coerce_mesh_name(ds_out2d)

    logging.info("Creating a grid object...")
    sx_ds = sx.Dataset(ds_out2d, sxgrid=sx.Grid(ds_out2d))

    logging.info("Creating a STRtree object from element centroids...")
    centroids = shapely.centroid(sx_ds.sxgrid.face_polygons)
    centroid_strtree = STRtree(centroids)

    list_da = []
    for polygon_name in polygons:
        logging.info(f"Finding elements in Polygon {polygon_name}...")
        flags = np.zeros(sx_ds.sxgrid.nMesh2_face, dtype=np.int8)
        polygon = polygons[polygon_name]
        centroids = centroid_strtree.query(polygon, predicate="contains")
        flags[centroids] = 1
        da = xr.DataArray(flags, dims=["nMesh2_face"])
        da.name = polygon_name
        list_da.append(da)
    ds = xr.merge(list_da)

    logging.info(f"Writing {subregion_nc}...")
    ds.to_netcdf(subregion_nc)

    logging.info(f"Done.")


if __name__ == "__main__":
    create_subregion_nc()
