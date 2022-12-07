
rem This needs to be edited to point to the actual location of the hgrid.gr3 file

download_noaa --stations sffpx mtyc1 pryc1 --syear 2009 --eyear 2011 --param elev --dest . || exit /b

gen_elev2D --stime 2009-05-01 --etime 2011-01-01 --hgrid ../../bay_delta/hgrid.gr3 --outfile elev2D.2021.th.nc --slr 0.0 noaa_pryc1*elev*.csv noaa_mtyc1*elev*.csv
