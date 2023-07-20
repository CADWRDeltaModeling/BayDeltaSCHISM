#!/bin/bash

display_help() {
    echo "Usage: $O [--date_base DATE_BASE] [--path_script PATH_SCRIPT] [--path_common PATH_COMMON]"
    echo "  --help       Display this help"
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        key="$1"

        case $key in
        --date_base)
            date_base="$2"
            shift 2
            ;;
        --path_script)
            path_script="$2"
            shift 2
            ;;
        --path_common)
            PATH_COMMON="$2"
            shift 2
            ;;
        --help)
            display_help
            exit 0
            ;;
        *)
            echo "Unknown option: $key"
            display_help
            exit 1
            ;;
        esac
    done
}

parse_arguments "$@"

# Set default values
if [ -z "$date_base" ]; then
    echo "Please specify date_base, for example, --date_base 2016-04-27"
    exit 1
fi
if [ -z "$path_script" ]; then
    path_script=${HOME}/pp_scripts
fi

if [ -z "$PATH_COMMON" ]; then
    PATH_COMMON=/mnt/local/simulations/common
fi

# Assume this suxarray environment can be activated
source activate suxarray

echo "Run HSI calculation..."
python ${path_script}/calculate_hsi2.py --path_study . --path_common $PATH_COMMON --date_base "2016-04-27" --date_start 2016-07-01 --date_end 2016-11-25

echo "Run HSI area calculation..."
python ${path_script}/calculate_hsi_area.py --path_out2d ${PATH_COMMON}/out2d_100.nc --path_hsi hsi.nc --path_common $PATH_COMMON

echo "Run LSZ calculation..."
python ${path_script}/calculate_lsz.py --path_out2d ${PATH_COMMON}/out2d_100.nc --path_salinity_nc depth_averaged_salinity_at_face.nc --path_common ${PATH_COMMON}

echo "Run 14d salt calculation..."
python ${path_script}/calculate_14d_salt.py --path_out2d ${PATH_COMMON}/out2d_100.nc --path_salinity_nc depth_averaged_salinity.nc --path_prefix_gr3 salt14d
