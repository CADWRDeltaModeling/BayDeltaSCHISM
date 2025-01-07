#!/bin/bash
module purge
module load intel/2024.0 hmpt/2.29 hdf5/1.14.3 netcdf-c/4.9.2 netcdf-fortran/4.6.1 schism/5.11.1
 
ulimit -s unlimited
NSCRIBES=7
SCHISM_BIN=pschism_PREC_EVAP_GOTM_TVD-VL
$SCHISM_BIN $NSCRIBES