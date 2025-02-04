#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Set the nudging links for a Bay-Delta SCHSIM model

2025-02-04: Customized
"""

import sys
import pandas as pd

from netCDF4 import Dataset
from schimpy.separate_species import separate_species
from schimpy.schism_mesh import read_mesh
from vtools import hours, days, seconds
from dms_datastore.read_ts import read_noaa, read_ts
import numpy as np
from datetime import datetime
import struct, argparse, re
import time 

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
                        required=False, help='Simulation directory path')
    return parser

def set_nudging(suffix, workdir='.'):
    """ This is a utility to set up nudging files based on a naming convention common for BayDeltaSCHISM
    
    Parameters
    ---------
    
    suffix: str
        This is the suffix used when preparing the nudging/gr files. For instance "obshycom" in SAL_nu_obshycom.nc
        
    workdir : str
        Directory where the links and changes are made        
        
    The script will identify nudging gr3 files and point the schism names to the suffix names. This 
    function depends on either a config or some conventions to define expectations. It also requires that
    we be able to identify the possibilities, either programatically or with a dictionaries for lookup,
    something like:
    
    target_link = {"SAL_nudge_{suffix}.gr3" : "SAL_nudge_{suffix}.gr3",
                   "TEM_nudge_{suffix}.gr3": "TEM_nudge_{suffix}.gr3",
                   "SAL_nu_{suffix}.nc" : "SAL_nu_{suffix}.nc",
                   "TEM_nu_{suffix}.nc": "TEM_nu_{suffix}.nc",               

    If it is easier to change the preprocessing scripts, let me know. Might want to ask Zhenlin and 
    Kijin what sediment or other tracers will look like. 
    It would be nice if that ended up here soon, but salt and temp are a win. Some connection with param
    could also be used, with the script printing out, perhaps early in the process,
    which variables are scheduled for nudging using
    nc files, and which are "nudge to IC" option. This could also be the basis of the search for variables
    beyond SAL_ and TEM_. Again, SAL and TEM are a win.
    
    One idea I have is that maybe the name "salinity_nudge_{suffix}.gr3" should be "SAL_nudge_{suffix}.gr3"
    or that SAL and TEM should be the only allowed exceptions. It would be helpful to have the
    expectation that usually the file names will be as-expected up to the suffix:
    "BLAH_nudge.gr3" -> "BLAH_nudge.gr3"

    """    

def main():
    parser = create_arg_parser()
    args = parser.parse_args()

    suffix = args.suffix
    workdir = args.workdir
    
    return set_nudging(suffix, workdir='.')

if __name__ == "__main__":
    main()
