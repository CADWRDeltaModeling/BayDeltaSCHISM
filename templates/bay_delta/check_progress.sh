# Get number of days from param.nml
# To run: bash check_progress.sh
param="$(readlink -f "./param.nml")"
runtime=$(cat $param | grep 'rnday = ' | grep -Eo '[0-9]*')

simtime=$(tail -n 21 outputs/mirror.out | grep 'TIME= ' | grep -Eo  '[0-9]*' | tail -2 | head -1)

# Convert simtime to days (floating-point division)
simtime_days=$(echo "scale=2; $simtime / (24*60*60)" | bc)

# Print result in console
printf "\n\t\tThe simulation has run $simtime_days out of $runtime days.\n"

# Check the fatal.error file:
if [ -s outputs/fatal.error ]; then
    printf "\n\n\t!! Errors found in fatal.error file:\n"
    cat outputs/fatal.error
else
    printf "\n\n\tNo errors found in fatal.error file.\n"
fi