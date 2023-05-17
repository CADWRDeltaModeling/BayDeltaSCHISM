import os
import datetime
byear = 2015 
eyear = 2017
bmonth= 11
emonth = 1 
bday = 18 
eday = 1

narr_src_dir = "/scratch/dms/BayDeltaSCHISM/Data/atmos/NARR"
new_src_dir = "/scratch/dms/BayDeltaSCHISM/Data/atmos/baydelta_sflux_v20180629"
link_dir = os.getcwd()

def make_links():
    start = datetime.date(byear,bmonth,bday)
    dt = datetime.timedelta(days=1)
    end = datetime.date(eyear,emonth,eday)
    current = start
    nfile = 0
    while (current <= end):  
        src_air = os.path.join(new_src_dir,"baydelta_schism_air_%s%02d%02d.nc" % (current.year, current.month, current.day))
#        if not os.path.exists(src_air):
#        src_air = os.path.join(narr_src_dir,"%4d_%02d/narr_air.%4d_%02d_%02d.nc" % (current.year,current.month,current.year,current.month,current.day))
        src_rad = os.path.join(narr_src_dir,"%4d_%02d/narr_rad.%4d_%02d_%02d.nc" % (current.year,current.month,current.year,current.month,current.day))
        src_str_prc = os.path.join(narr_src_dir,"%4d_%02d/narr_prc.%4d_%02d_%02d.nc" % (current.year,current.month,current.year,current.month,current.day))
        nfile += 1
        link_air = os.path.join(link_dir,"sflux_air_1.%04d.nc" % (nfile))
        link_rad = os.path.join(link_dir,"sflux_rad_1.%04d.nc" % (nfile))
        link_str_prc = os.path.join(link_dir, "sflux_prc_1.%04d.nc" % (nfile))
        if not os.path.exists(link_air):
            os.symlink(src_air, link_air)
        if not os.path.exists(link_rad):
            os.symlink(src_rad, link_rad)
        if not os.path.exists(link_str_prc):
            os.symlink(src_str_prc, link_str_prc)
        current += dt


if __name__ == "__main__":
    make_links()
