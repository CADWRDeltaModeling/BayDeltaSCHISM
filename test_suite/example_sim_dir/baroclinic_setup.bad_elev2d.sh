#!/bin/sh
set -e

# LOAD CONDA ENVIRONMENT PRIOR TO RUNNING THIS BASH SCRIPT

# LINK OCEAN BOUNDARY ----------------------------------
ln -sf example.bad_start.elev2D.th.nc elev2D.th.nc

# run script to create uv3d.th.nc
ulimit -s unlimited

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