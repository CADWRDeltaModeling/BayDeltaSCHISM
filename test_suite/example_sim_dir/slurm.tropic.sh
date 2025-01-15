#!/bin/bash
#SBATCH --job-name=bdschism_test_suite_sim_dir     # Job name
#SBATCH --partition=work        # Partition name to submit the job
#SBATCH --mail-type=NONE            # Mail events (NONE, BEGIN, END, FAIL, ALL)
#SBATCH --mail-user=lily.tomkovic@water.ca.gov       # Where to send mail
#SBATCH --ntasks=224                      # Number of MPI ranks (or cores) (192)
#SBATCH --nodes=7                       # Number of nodes (6)
#SBATCH --ntasks-per-node=32             # How many tasks on each node
#SBATCH --output=bdschism_test_suite_sim_dir_%j.log     # Standard output and error log

module load intel/2024.0
module load hmpt/2.29
 
mpirun bash schism.sh