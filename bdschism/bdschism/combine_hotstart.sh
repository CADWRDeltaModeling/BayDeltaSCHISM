#!/bin/bash
################################################################################
# Script: combine_hotstart.sh
# Description: This script prepares a hotstart file for a simulation based on
# user input.
################################################################################

# Usage function
usage() {
    echo "Usage: $0 <days>"
    echo "  <days>: Number of days for the simulation."
    echo ""
    echo "  Prepare a hotstart file for a simulation based on user input."
    echo ""
    echo "  The script will look for the last uncombined hotstart from outputs directory"
    echo "  and compare with the user input. If the user input is greater than the last"
    echo "  available hotstart files, the last hotstart file will be used instead."
    echo "  The script needs to be run in a study directory where the outputs directory is located."
}

# Check if the user provided the number of days as an argument
if [ -z "$1" ]; then
    usage
    exit 1
fi

simulation_days="$1"

# NOTE that the following variables are hard-coded.
SECONDS_PER_DAY=86400
NHOT_WRITE=4800
DT=90

# Directory containing uncombined hotstart files. Hard-coded.
DIR_OUTPUTS="outputs"

# Find the most recent file whose name begins with "hotstart_000000"
recent_file=$(ls -t "${DIR_OUTPUTS}"/hotstart_000000* 2>/dev/null | head -n1)

# Check if a file is found
if [ -n "$recent_file" ]; then
    # Extract string following "_" from the file name
    extracted_string=$(echo "$recent_file" | sed 's/^.*000000_//')
else
    echo "No files found whose name begins with 'hotstart' in $DIR_OUTPUTS"
    exit 1
fi

last_iteration=$(echo "$extracted_string" | grep -oE '[0-9]+\.nc' | sed 's/\.nc//')
last_day=$((($last_iteration * $DT) / $SECONDS_PER_DAY))

# Obtain valid output date closest to user input
output_interval=$((($NHOT_WRITE * $DT) / $SECONDS_PER_DAY))
simulation_days=$((($simulation_days / $output_interval) * $output_interval))

# Obtain number of iterations
iterations=$((($simulation_days * SECONDS_PER_DAY) / DT))

# If the requested iteration does not exist, use the latest file instead.
if [ "$iterations" -gt "$last_iteration" ]; then
    echo "There is no hotstart input with it=$iterations (day $simulation_days)."
    echo "Using the most recently generated hotstart input instead: it=$last_iteration (day $last_day)."
    iterations=$last_iteration
    simulation_days=$last_day
fi

# Generate hotstart file
echo "Generating 'hotstart_it=$iterations.nc' (day $simulation_days)"
cd $DIR_OUTPUTS
hotstart_input="hotstart_000000_$iterations.nc"
if [ ! -f "$hotstart_input" ]; then
    echo "Hotstart files to combine not found: $DIR_OUTPUTS/$hotstart_input"
    echo "Please check the outputs directory."
    exit 1
fi
combine_hotstart7 -i $iterations
HOTSTART_OUTPUT="hotstart_it=$iterations.nc"
if [ -f "$HOTSTART_OUTPUT" ]; then
    echo "Hotstart file generated: $HOTSTART_OUTPUT"
    cd ..
    ln -sf "${DIR_OUTPUTS}/${HOTSTART_OUTPUT}" hotstart.nc
else
    echo "Failed to generate hotstart file: $HOTSTART_OUTPUT"
    exit 1
fi
