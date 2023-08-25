#!/usr/bin/env python
import os
import datetime
byear = 2018
eyear = 2019
bmonth= 5
emonth = 1
bday = 7
eday = 1

src_dir = "/scratch/dms/BayDeltaSCHISM/Data/atmos/baydelta_sflux_v20190802"
src_dir_narr = "/scratch/dms/BayDeltaSCHISM/Data/atmos/NARR"
link_dir = os.getcwd()

def make_links():
    start = datetime.date(byear,bmonth,bday)
    dt = datetime.timedelta(days=1)
    end = datetime.date(eyear,emonth,eday)
    current = start
    if (current >= end):
        print(f'ERROR: Start date {start.strftime("%b %d, %Y")} is after end date {end.strftime("%b %d, %Y")}')
    nfile = 0
    while (current <= end):
        # Air data
        # Ours
        src_str_air = os.path.join(src_dir,"baydelta_schism_air_%s%02d%02d.nc" % (current.year, current.month, current.day))
        # NARR
        # src_str_air = os.path.join(src_dir_narr, "%4d_%02d/narr_air.%4d_%02d_%02d.nc" % (current.year, current.month, current.year, current.month, current.day))
        src_str_rad = os.path.join(src_dir_narr, "%4d_%02d/narr_rad.%4d_%02d_%02d.nc" % (current.year, current.month, current.year, current.month, current.day))
        src_str_prc = os.path.join(src_dir_narr, "%4d_%02d/narr_prc.%4d_%02d_%02d.nc" % (current.year, current.month, current.year, current.month, current.day))
        nfile += 1
        link_str_air = os.path.join(link_dir, "sflux_air_1.%04d.nc" % (nfile))
        link_str_rad = os.path.join(link_dir, "sflux_rad_1.%04d.nc" % (nfile))
        link_str_prc = os.path.join(link_dir, "sflux_prc_1.%04d.nc" % (nfile))
        if not os.path.exists(link_str_air):
            os.symlink(src_str_air, link_str_air)
        if not os.path.exists(link_str_rad):
            os.symlink(src_str_rad, link_str_rad)
        if not os.path.exists(link_str_prc):
            os.symlink(src_str_prc, link_str_prc)
        current += dt


if __name__ == "__main__":
    make_links()
