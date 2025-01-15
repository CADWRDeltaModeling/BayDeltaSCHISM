#!/bin/sh
set -e

# LOAD CONDA ENVIRONMENT PRIOR TO RUNNING THIS BASH SCRIPT

# CREATE OCEAN BOUNDARY ----------------------------------

## this has already been run in earliler iterations but is kept here to show where the data comes from
# download_noaa --syear 2013 --eyear 2013 --param water_level noaa_stations.txt 

# generate .th.nc file
# gen_elev2d --outfile example.elev2D.th.nc --hgrid=hgrid.gr3 --stime=2013-10-24 --etime=2013-10-31 ./noaa_download/noaa_pryc1_9415020_water_level_2013_2014.csv ./noaa_download/noaa_mtyc1_9413450_water_level_2013_2014.csv
ln -sf example.elev2D.th.nc elev2D.th.nc

# CREATE OTHER SYMBOLIC LINKS ----------------------------
# shared spatial inputs
ln -sf bctides.in.2d bctides.in
ln -sf vgrid.in.2d vgrid.in

# add gr3 links
ln -sf salinity_nudge_roms.gr3 SAL_nudge.gr3
ln -sf temperature_nudge_roms.gr3 TEM_nudge.gr3

# modified TH inputs
ln -sf delta_cross_channel_gates.th delta_cross_channel.th
ln -sf vsink.good.th vsink.th
ln -sf vsource.good.th vsource.th
ln -sf source_sink.good.in source_sink.in
ln -sf montezuma_radial.good.th montezuma_radial.th
ln -sf montezuma_boat_lock.good.th montezuma_boat_lock.th
ln -sf montezuma_flash.good.th montezuma_flash.th
ln -sf ccfb.th ccfb_gate.th


# inputs specific to this setup
ln -sf param.nml.tropic param.nml

# CHECK OUTPUT DIRECTORY IS PRESENT ----------------------

mkdir -p outputs # only creates outputs if it's not preset

# model runs with slurm