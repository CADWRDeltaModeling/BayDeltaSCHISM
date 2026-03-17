#!/bin/bash
#SBATCH --job-name=uv3d_batch                                           # job name used to track job progress in sbatch
#SBATCH --partition=work                                                # job partition
#SBATCH --array=1-797                                                   # number of days from outputs to use to generate uv3D.th.nc
#SBATCH --ntasks=1                                                      # 1 task
#SBATCH --cpus-per-task=1                                               # 1 cpu per task is plenty
#SBATCH --output=./_slurm_logs/slurm_uv3d_%A_%a.log                     # creates a folder of logs per task
#SBATCH --mail-type=NONE                                                # NONE - no emails sent on completion (too many jobs)

set -eo pipefail

conda activate schism                                                   # conda environment with bdschism
set -u

export SIM_DIR="/path/to/simulations"                                   # set the directory to your simulations

nfile="$SLURM_ARRAY_TASK_ID"                                            # inherited per task from array numbers (above)

run_uv3d_if_in_range() {
	local sim_name="$1"                                                 # pass the name of the simulation folder (ex: /path/to/simulations/sim_name)
	local run_dir="${SIM_DIR}/${sim_name}"                              # run_dir path to sim_name
	local param_file="${run_dir}/param.nml"                             # path to param.nml in run_dir

	if [[ ! -f "$param_file" ]]; then
		echo "[SKIP] ${sim_name}: missing ${param_file}"
		return 0
	fi

	local rnday_int
	rnday_int=$(awk '
		BEGIN { IGNORECASE=1 }
		/^[[:space:]]*!/ { next }
		{
			gsub(/!.*$/, "")
			if (match($0, /rnday[[:space:]]*=[[:space:]]*([0-9]+(\.[0-9]+)?)/, m)) {
				print int(m[1])
				exit
			}
		}
	' "$param_file")                                                    # gather rnday_int from param.nml rnday

	if [[ -z "$rnday_int" ]]; then
		echo "[SKIP] ${case_name}: could not parse rnday from ${param_file}"
		return 0
	fi

	if (( nfile <= rnday_int )); then
		echo "[RUN]  ${case_name}: nfile=${nfile}, rnday=${rnday_int}"
		cd "$run_dir"
		bds uv3d_single "$nfile" -o outputs.tropic/uv3d --overwrite     # compute single uv3d file from $nfile
	else
		echo "[SKIP] ${case_name}: nfile=${nfile} > rnday=${rnday_int}"
	fi
}


# Pass whichever simulation folders you want to calculate uv3D.th.nc files from
run_uv3d_if_in_range "simulation_name_1"
run_uv3d_if_in_range "simulation_name_2"
