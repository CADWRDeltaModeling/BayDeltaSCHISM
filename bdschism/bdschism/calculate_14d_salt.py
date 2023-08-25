from pathlib import Path
import logging
import argparse
import xarray as xr

# import suxarray as sx
# import suxarray.helper

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


def create_argparser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--path_out2d", type=lambda s: Path(s))
    argparser.add_argument("--path_salinity_nc", type=lambda s: Path(s))
    argparser.add_argument("--path_prefix_gr3", type=str)
    return argparser


def main():
    argparser = create_argparser()
    args = argparser.parse_args()

    path_out2d = args.path_out2d
    path_salinity_nc = args.path_salinity_nc
    path_prefix_gr3 = args.path_prefix_gr3

    ds_out2d = xr.open_dataset(path_out2d)
    # if sx.get_topology_variable(ds_out2d) is None:
    #     ds_out2d = sx.add_topology_variable(ds_out2d)
    # ds_out2d = sx.coerce_mesh_name(ds_out2d)

    # logging.info("Creating a grid object...")
    # sx_ds = sx.Dataset(ds_out2d, sxgrid=sx.Grid(ds_out2d))

    logging.info("Reading postprocessed depth-averaged data...")
    chunks = {"time": 48}
    ds_salinity = xr.open_dataset(path_salinity_nc, chunks=chunks)
    da_salinity = ds_salinity["depth_averaged_salinity"]

    year = da_salinity.time.values[0].astype("datetime64[Y]").astype(int) + 1970
    months = range(7, 12)
    for month in months:
        logging.info(f"Calculating 14-day average for month {year}/{month}...")
        time_slice = slice(f"{year}-{month}-01", f"{year}-{month}-14")
        da_salinity_average = da_salinity.sel(time=time_slice).mean(dim="time")
        path_gr3 = path_prefix_gr3 + f"_{year}{month:02d}.gr3"
        write_to_gr3(path_gr3, ds_out2d, da_salinity_average)

    logging.info("Done")


def write_to_gr3(path_gr3, ds_out2d, da_salinity_avarege):
    with open(path_gr3, "w") as fout:
        line = "salinity_14d_average\n"
        fout.write(line)
        n_elems = ds_out2d.nSCHISM_hgrid_face.size
        n_nodes = ds_out2d.nSCHISM_hgrid_node.size
        line = f"{n_elems} {n_nodes}\n"
        fout.write(line)

        x = ds_out2d.SCHISM_hgrid_node_x.values
        y = ds_out2d.SCHISM_hgrid_node_y.values
        z = da_salinity_avarege.values
        conn = ds_out2d.SCHISM_hgrid_face_nodes.values
        for i_node in range(n_nodes):
            line = f"{i_node+1} {x[i_node]} {y[i_node]} {z[i_node]}\n"
            fout.write(line)
        for i_elem in range(n_elems):
            # Filter -1 values
            valid = conn[i_elem, :] != -1
            c = conn[i_elem, valid]
            line = f"{i_elem+1} {len(c)} " + " ".join([str(i) for i in c]) + "\n"
            fout.write(line)


if __name__ == "__main__":
    main()
