#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Set the nudging links for a Bay-Delta SCHSIM model

2025-02-04: Customized
"""

from datetime import datetime
import argparse

import schimpy.param as parms
import bdschism.settings as config

import os

################# command line application #####################

def create_arg_parser():
    import textwrap
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
         ============== Example ==================
      > set_nudging.py --suffix obshycom --workdir .
      """),
        description="""The script will identify nudging gr3 files and point the schism names to the suffix names."""
    )
    parser.add_argument('--suffix', default=None, required=True,
                        help="the suffix desired for the nudging/gr3 files. Ex: 'obshycom' in SAL_nu_obshycom.nc")
    parser.add_argument('--workdir', default='.', required=False, 
                        help='Simulation directory path')
    parser.add_argument('--var_map', default="", type=parse_var_map, required=False, 
                        help="Any unexpected mapping in key=value pairs separated by commas. Ex: --var_map 'TEM=temperature,SAL=salinity'")
    return parser

def parse_var_map(s):
    """
    Parse a string of key=value pairs separated by commas into a dictionary.
    Expected format: "key1=value1,key2=value2"
    Used for var_map which feeds the gr3 formats for things like TEM=temperature
    """
    mapping = {}
    if s!="":
        # Remove any surrounding quotes or spaces and split by comma
        pairs = s.split(',')
        for pair in pairs:
            print(pair)
            if '=' not in pair:
                raise argparse.ArgumentTypeError(
                    f"Invalid format for var_map: '{pair}'. Expected format key=value."
                )
            key, value = pair.split('=', 1)
            mapping[key.strip()] = value.strip()
    return mapping

def get_nudge_list(workdir):
    fname = os.path.join(workdir,"param.nml")
    
    params = parms.read_params(fname)
    nc_nudge_list = []
    nc_dict = {1: 'TEM',
               2: 'SAL',
               3: 'GEN',
               4: 'AGE',
               5: 'SED',
               6: 'ECO',
               7: 'ICM',
               8: 'COS',
               9: 'FIB',
               10: 'TIMOR-NOT-ACTIVE',
               11: 'FBM'}

    for i in range(1, 12):
        if params._namelist['OPT'][f'inu_tr({i})']['value'] == 2:
            nc_nudge_list.append(nc_dict[i])

    return nc_nudge_list

def set_nudging(suffix, workdir='.', var_map={}):
    """ This is a utility to set up nudging files based on a naming convention common for BayDeltaSCHISM. 
    Assumed this is on Linux or admin-priveleged Windows machine.
    
    Parameters
    ---------
    
    suffix: str
        This is the suffix used when preparing the nudging/gr files. For instance "obshycom" in SAL_nu_obshycom.nc
        
    workdir : str
        Directory where the links and changes are made        

    """ 

    nc_nudge_list = get_nudge_list(workdir)
    check_files = []
    gr3_color = "\033[36m"  # Light blue for gr3
    nc_color = "\033[34m"  # Dark blue for nc
    reset_color = "\033[0m"  # Reset color

    for MOD in nc_nudge_list:
        if MOD in var_map.keys():
            var_in_gr3 = var_map[MOD]
        else:
            var_in_gr3 = MOD

        var_gr3_in = "{var_in_gr3}_nudge_{suffix}.gr3".format(**locals())
        var_nc_in = "{MOD}_nu_{suffix}.nc".format(**locals())
        check_files.extend([var_gr3_in, var_nc_in])

        var_gr3_out = "{MOD}_nudge.gr3".format(**locals())
        var_nc_out = "{MOD}_nu.nc".format(**locals())

        print(f"\t{gr3_color}{MOD} .gr3{reset_color}: Linked {var_gr3_out} to {var_gr3_in}")
        config.create_link(var_gr3_in, os.path.join(workdir,var_gr3_out) )
        print(f"\t{nc_color}{MOD} .nc{reset_color}: Linked {var_nc_out} to {var_nc_in}")
        config.create_link(var_nc_in, os.path.join(workdir,var_nc_out))

    invalid_files = [cf for cf in check_files if not os.path.exists(os.path.join(workdir, cf))]

    if invalid_files:
        red_color = "\033[91m"   # Red for main message
        pink_color = "\033[95m"  # Pink for filenames

        error_message = (
            f"{red_color}The following files are not in the directory:\n"
            + "\n".join(f"\t{pink_color}- {file}{reset_color}" for file in invalid_files)
        )

        raise ValueError(error_message)


def main():
    parser = create_arg_parser()
    args = parser.parse_args()

    suffix = args.suffix
    workdir = args.workdir
    var_map = args.var_map
    
    return set_nudging(suffix, workdir='.',var_map=var_map)

if __name__ == "__main__":
    main()
    # set_nudging('roms', workdir='path_to_schism_sim_dir')
