#!/usr/bin/env python
# -*- coding: utf-8 -*-

def uv3d(outloc='./outputs',)
    """Interpolate velocity from background (prior) grid to foreground (new)
    This is used to move boundary data from a completed barotropic run 
    into a uv3D.th.nc file for a baroclinic run. Special case of interpolate variables"""
    raise NotImplementedError()
    

def interpolate_variables():
    """Runs the nested variables script interpolate_variables to inteprolate from one grid to another"""
    raise NotImplementedError()


def barotropic():
    """ Ensures that key links are set for a barotropic run. 
    This requires predetermined (but configurable) 
    filenames for param.nml (param.nml.tropic),
    vgrid.in (vgrid.in.2d) and bctides.in (e.g. bctides.in.tropic).
    
    The script will check that the vgrid is 2d, bctides has no scalars enabled 
    and typical param.nml parameters are set (dt, transport, outputs for uv3D etc). 
    The expectations are configurable but defaults will do in typical cases. 
    
    No unrelated runtime checking is performed.
    """ 
    
def link_atmospheric():
    """ Creates links to atmospheric files. Temporal breakpoints in the sources are allowed """
    

def link_nudging():
    """ Creates links to nudging files with expected SCHISM names
    based on the nudging suffix and a configurable templated name """
    


def hotstart_inventory():
    """ Creates user-readable expected inventory of hotstart files
    either preliminary based on param.nml file 
    or actual based param.nml plus doing a file listing """

def tropic_prerun_checks():
    """ Checks mean of SF water level, something about CCF? outputs exists, """


def prep_launch_file():
    """ Coordinate with Nicky's stuff for Azure"""
    
def clinic_postrun_checks():
    """ Not yet determined """






    

    



