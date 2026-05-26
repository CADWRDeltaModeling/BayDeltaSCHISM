#!/bin/bash
#SBATCH --job-name=uv3d_batch                                           # job name used to track job progress in sbatch
#SBATCH --partition=work                                                # job partition
#SBATCH --array=1-797                                                   # number of days from outputs to use to generate uv3D.th.nc
#SBATCH --ntasks=1                                                      # 1 MPI rank per array element (interpolate_variables is serial, not MPI)
#SBATCH --cpus-per-task=1                                               # serial
#SBATCH --output=./_slurm_logs/slurm_uv3d_%A_%a.log                     # creates a folder of logs per task
#SBATCH --mail-type=NONE                                                # NONE - no emails sent on completion (too many jobs)

set -eo pipefail

# conda activate requires shell functions that .bashrc normally provides.
# Source the init script explicitly since SLURM runs a non-interactive shell.
source ~/miniconda3/etc/profile.d/conda.sh
conda activate schism
set -u

# ===========================================================================
# Configuration — edit these before submitting
# ===========================================================================

# Background (barotropic / source) simulation.
# Velocity outputs and grid files are READ from here.
BG_DIR="/path/to/barotropic_sim"
BG_OUTPUT_DIR=""            # output subdirectory inside BG_DIR
                            #   leave empty to auto-detect (tries outputs.tropic, then outputs)
BG_HGRID="hgrid.gr3"       # hgrid file in BG_DIR, linked as bg.gr3
BG_VGRID="vgrid.in.2d"     # 2-D (barotropic) vgrid in BG_DIR, linked as vgrid.bg

# Foreground (baroclinic / destination) simulation.
# Target grid onto which velocities are interpolated.
FG_DIR="/path/to/baroclinic_sim"
FG_HGRID="hgrid.gr3"       # hgrid file in FG_DIR, linked as fg.gr3
                            #   often identical to BG_HGRID when grids are shared
FG_VGRID="vgrid.in.3d"     # 3-D (baroclinic) vgrid in FG_DIR, linked as vgrid.fg
FG_OUT_DIR="${FG_DIR}/uv3d" # directory where uv3d_<N>.th.nc files are written

# ===========================================================================

nfile="$SLURM_ARRAY_TASK_ID"

# Parse rnday from BG param.nml — the bg run determines the valid output range.
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
' "${BG_DIR}/param.nml")

if [[ -z "$rnday_int" ]]; then
	echo "[ERROR] Could not parse rnday from ${BG_DIR}/param.nml"
	exit 1
fi

if (( nfile > rnday_int )); then
	echo "[SKIP] nfile=${nfile} > rnday=${rnday_int}"
	exit 0
fi

echo "[RUN] nfile=${nfile}, rnday=${rnday_int}"
echo "      bg=${BG_DIR}"
echo "      fg=${FG_DIR}"

# Pass --bg-output-dir only when explicitly set; otherwise let single_uv3d
# auto-detect (tries outputs.tropic first, then outputs).
bg_output_dir_arg=()
[[ -n "$BG_OUTPUT_DIR" ]] && bg_output_dir_arg=( --bg-output-dir "$BG_OUTPUT_DIR" )

bds uv3d_single "$nfile"  \
	--bg-dir   "$BG_DIR"   \
	--fg-dir   "$FG_DIR"   \
	--hgrid-bg "$BG_HGRID" \
	--hgrid-fg "$FG_HGRID" \
	--vgrid-bg "$BG_VGRID" \
	--vgrid-fg "$FG_VGRID" \
	"${bg_output_dir_arg[@]}" \
	-o         "$FG_OUT_DIR" \
	--overwrite
