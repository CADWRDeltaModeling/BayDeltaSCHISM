#!/bin/bash
#PBS -q workq
#PBS -N schismbcg
#PBS -l select=3:ncpus=24:mpiprocs=24
#PBS -M hansang.kim@water.ca.gov
#PBS -m abe

n_cores=72
cd $PBS_O_WORKDIR
module purge
module use /opt/intel/oneapi/modulefiles
module load compiler/2022.1.0
module load mpi/2021.6.0
# I_MPI_HYDRA_IFACE=ib0 MV2_DEFAULT_TIME_OUT=20 mpiexec --rsh=ssh -n $n_cores bash ./schism.sh
mpiexec --rsh=ssh -n $n_cores bash ./schism.sh.sed
