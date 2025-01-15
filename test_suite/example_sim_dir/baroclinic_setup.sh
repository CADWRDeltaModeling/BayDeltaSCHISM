#!/bin/sh
set -e

# LOAD CONDA ENVIRONMENT PRIOR TO RUNNING THIS BASH SCRIPT

# CREATE OCEAN BOUNDARY ----------------------------------

## this has already been run in earliler iterations but is kept here to show where the data comes from
# download_noaa --syear 2013 --eyear 2013 --param water_level noaa_stations.txt 

# generate .th.nc file
# gen_elev2d --outfile example.elev2D.th.nc --hgrid=hgrid.gr3 --stime=2013-10-24 --etime=2013-10-31 ./noaa_download/noaa_pryc1_9415020_water_level_2013_2014.csv ./noaa_download/noaa_mtyc1_9413450_water_level_2013_2014.csv
ln -sf example.elev2D.th.nc elev2D.th.nc

# run script to create uv3d.th.nc
ulimit -s unlimited

# START interp commands
[ "$1" == "interp" ] && 
# CHANGE OUTPUTS DIR -------------------------------------
mkdir -p outputs_tropic && 
mv outputs/* outputs_tropic && 
mkdir -p outputs &&
	

# CREATE OCEAN BOUNDARY ----------------------------------

cd outputs_tropic &&
rsync -avz ../interpolate_variables.in . &&

# link necessary files
ln -sf ../hgrid.gr3 bg.gr3 &&
ln -sf ../hgrid.gr3 fg.gr3 &&
ln -sf ../vgrid.in.2d vgrid.bg &&
ln -sf ../vgrid.in.3d vgrid.fg &&

interpolate_variables8 # this takes quite a while

# Check if the directory name is "outputs_tropic"
if [[ "$(basename "$PWD")" == "outputs_tropic" ]]; then
cp uv3D.th.nc ../uv3D.th.nc &&
cd ../
fi
# END !no-interp commands

# Re link barotropic files -------------------------------

# modified TH inputs
ln -sf delta_cross_channel_gates.th delta_cross_channel.th
ln -sf vsink.good.th vsink.th
ln -sf vsource.good.th vsource.th
ln -sf source_sink.good.in source_sink.in
ln -sf montezuma_radial.good.th montezuma_radial.th
ln -sf montezuma_boat_lock.good.th montezuma_boat_lock.th
ln -sf montezuma_flash.good.th montezuma_flash.th
ln -sf ccfb.th ccfb_gate.th


# CREATE CLIINIC SYMBOLIC LINKS ----------------------------

# add new links
ln -sf SAL_nu_roms.nc SAL_nu.nc
ln -sf salinity_nudge_roms.gr3 SAL_nudge.gr3
ln -sf TEM_nu_roms.nc TEM_nu.nc
ln -sf temperature_nudge_roms.gr3 TEM_nudge.gr3
ln -sf hotstart_20131024.nc hotstart.nc

# change existing links
ln -sf bctides.in.3d bctides.in
ln -sf vgrid.in.3d vgrid.in
ln -sf param.nml.clinic param.nml

# model runs with slurm