#!/bin/bash
#SBATCH --job-name=schism       # Job name
#SBATCH --partition=work        # Partition name to submit the job
#SBATCH --mail-type=END,FAIL            # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=john.doe@email.com       # Where to send mail
#SBATCH --ntasks=192                      # Number of MPI ranks (or cores)
#SBATCH --nodes=6                       # Number of nodes
#SBATCH --ntasks-per-node=32             # How many tasks on each node
#SBATCH --output=slurm_log_%j.log     # Standard output and error log
 
module load intel/2024.0
module load hmpt/2.29
 
mpirun bash schism_hmpt_hpc5.sh