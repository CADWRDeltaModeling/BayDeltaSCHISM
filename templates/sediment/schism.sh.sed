#!/bin/sh
module purge
module use /opt/intel/oneapi/modulefiles
module load schism/5.10_intel2022.1
ulimit -s unlimited
NSCRIBES=20
SCHISM_BIN=pschism_SED_PREC_EVAP_GOTM_TVD-VL
$SCHISM_BIN $NSCRIBES