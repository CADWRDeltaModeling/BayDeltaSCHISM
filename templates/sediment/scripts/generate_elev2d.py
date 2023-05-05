# This script download data from NOAA and generate elev2D.th.nc.
# Note: This script uses a bit old version of Vtools to download NOAA data.
# As of 2021-08-10, the current HEAD of Vtools uses the new unified download
# routines, which are quite different from the old version (#610110e).
import datetime
import pandas as pd
from dms_datastore import download_noaa
import schimpy.gen_elev2D


def main():
    stime = datetime.datetime(2015, 11, 18)
    etime = datetime.datetime(2017, 1, 1)
    pad = datetime.timedelta(days=30)

    # Download data
    # stations = ["9415020", "9413450"]
    stations = pd.DataFrame({
        "agency_id" : ["9415020", "9413450"],
        "station_id" : ["PointReyes", "Monterey"],
        "src_var_id" : ["water_level", "water_level"],
        "name" : ["", ""],
        "param" : ["elev", "elev"],
        "subloc" : ["default", "default"]
    })
    product = "water_level"
    start = stime - pad
    end = etime + pad
    download_noaa.noaa_download(stations, ".",
                                                 start=start, end=end)

    # Generate elev2D
    hgrid_fpath = "../hgrid.gr3"
    fpath_out = "../elev2D.th.nc"
    pt_reyes_fpath = "noaa_pointreyes_9415020_elev_2015_2017.csv"
    monterey_fpath = "noaa_monterey_9413450_elev_2015_2017.csv"
    slr = 0.
    schimpy.gen_elev2D.gen_elev2D(hgrid_fpath, fpath_out,
                                  pt_reyes_fpath, monterey_fpath,
                                  stime, etime, slr)


if __name__ == "__main__":
    main()
