Scripts for postprocessing, particularly for Bay-Delta specific projects

gen_lsz_zone.py: create a netcdf file with lsz flag over a specified period.

gen_lsz_zone_ts.py: create a netcdf file with lsz flag over a specified period, and output
                    lsz arcrage over the period for 5 sub regions defined by subregion.nc.
                                       
gen_zone_flags.py: You need to run this script before run gen_lsz_zone_ts.py to generate zone flag
                   nc file subregion.nc. This script will read subregion polygon points UTM_XY defined
                   in 5 txt file,cache_mzm_link_points.txt,north_arc_points.txt,suisun_bay_points.txt,
                   delta_points.txt and suisun_marsh_points.txt. It need a schism output file as input
                   to get your schism model mesh.
