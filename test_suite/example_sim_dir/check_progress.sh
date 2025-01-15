# Get number of days from param.nml
# To run: bash check_progress.sh
param="$(readlink -f "./param.nml")"
runtime=$(cat $param | grep 'rnday = ' | grep -Eo '[0-9]*')

# find latest simulation output time stamp from mirror.out
simtime=$(tail -n 21 outputs/mirror.out | grep 'TIME= ' | grep -Eo  '[0-9]*' | tail -2 | head -1)

simtime=$((simtime/24/60/60)) 

# Print result in console
printf "\n\t\tThe simulation has run $simtime out of $runtime days.\n"