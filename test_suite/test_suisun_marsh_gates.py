import pytest
import os
import sys
import pandas as pd
from schimpy.schism_source import read_sources
from vtools import elapsed_datetime,days


def read_th_gate(fname,names):
    return pd.read_csv(fname,index_col=0,
                       sep=r'\s+',comment='#',
                       names=names,header=None)

@pytest.fixture(scope="module")
def marsh_gate_dfs(sim_dir,params):
    """ Reads vsource, vsink and msource.th files and returns as list of DataFrames"""
    start = params.run_start
    radial = read_th_gate(os.path.join(sim_dir,"montezuma_radial.th"),
                          names=["install","ndup","radial_down","radial_up","elev","width","height"])

    flash =  read_th_gate(os.path.join(sim_dir,"montezuma_flash.th"),
                        names=["install","ndup","flash_down","flash_up","elev","width"])

    boatlock = read_th_gate(os.path.join(sim_dir,"montezuma_boat_lock.th"),
                        names=["install","ndup","boatlock_down","boatlock_up","elev","width"]) 

    marsh = pd.concat((radial[['radial_down','radial_up']],
                       boatlock[['boatlock_down','boatlock_up']],
                       flash[['flash_down','flash_up']]),axis=1).sort_index()
    marsh['elapsed'] = marsh.index

    marsh  = elapsed_datetime(marsh,reftime=params.run_start).ffill()
    # ffill leaves a few values with elapsed < 0 unfilled. Fix this with bfill 
    marsh.update(marsh.loc[marsh.elapsed<0,:].bfill(),overwrite=False)

    return marsh


@pytest.mark.prerun
def test_boatlock_flash_self_consistent(sim_dir,marsh_gate_dfs):
    pd.set_option('display.max_columns', 8)
    boatlock_consistent = (marsh_gate_dfs.boatlock_down == marsh_gate_dfs.boatlock_up).all(axis=None)
    flash_consistent = (marsh_gate_dfs.flash_down == marsh_gate_dfs.flash_up).all(axis=None)
    if not(boatlock_consistent and flash_consistent):
        print(marsh_gate_dfs,file=sys.stderr)
    assert boatlock_consistent, "Boatlock op_down and op_up typically must be the same always"
    assert flash_consistent, "Flashboard op_down and op_up typically must be the same always"


@pytest.mark.prerun
def test_radial_seldom_closed(sim_dir,marsh_gate_dfs):
    radial_seldom_closed =  (marsh_gate_dfs.radial_up) == 0 & (marsh_gate_dfs.radial_down == 0)
    total_closed = radial_seldom_closed.groupby(radial_seldom_closed.index.year).sum()
    #assert 1==2

    # TODO: make the # days depend on planning and/or groupby years 
    assert (radial_seldom_closed < 10).all(),f"Radial gate closed both directions longer than plausible ({total_closed} days)."




@pytest.mark.prerun
def test_radial_flash_consistent(sim_dir,marsh_gate_dfs):
    radial_op = (marsh_gate_dfs.radial_down > 0) & (marsh_gate_dfs.radial_up == 0.)
    flash_out = (marsh_gate_dfs.flash_down > 0.01)
    radial_flash_incons = (radial_op & flash_out)
    if radial_flash_incons.any():
        #print(marsh_gate_dfs,file=sys.stderr)
        print(radial_flash_incons.index[0])
        first_occur = marsh_gate_dfs.index[radial_flash_incons][0]
        first_elapsed = marsh_gate_dfs.loc[first_occur,"elapsed"]
        print("Inconsistent Radial/Flashboard (timestamps are the union of radial/flash/boatlock timestamps):",file=sys.stderr)
        print(marsh_gate_dfs.loc[radial_flash_incons,["elapsed","radial_down","radial_up","flash_down","flash_up"]],file=sys.stderr)
    assert ~radial_flash_incons.any(axis=None), f"Flashboard must be in/closed (op=0) when radial gate operates. First problem is {first_occur} at elapsed time {first_elapsed}"



@pytest.mark.prerun
def test_boatlock_flash_consistent(sim_dir,marsh_gate_dfs):
    pd.set_option('display.max_columns', 8)
    flash_open_boatlock_closed = (marsh_gate_dfs.flash_down > 0) & (marsh_gate_dfs.boatlock_down == 0) 
    boatlock_open_flash_closed = (marsh_gate_dfs.flash_down == 0) & (marsh_gate_dfs.boatlock_down > 0)
    pdec=pd.concat((boatlock_open_flash_closed,
                    flash_open_boatlock_closed),axis=1)
    pdec['elapsed'] = marsh_gate_dfs.elapsed
    boatlock_flash = (flash_open_boatlock_closed | boatlock_open_flash_closed)      # one or the other is closed
    boatlock_flash &=  ~(flash_open_boatlock_closed & boatlock_open_flash_closed)   # but not both
    if not (boatlock_flash.all(axis=None)):
        
        boatlock_flash = pd.concat((boatlock_flash,marsh_gate_dfs.elapsed),axis=1)
        #print(boatlock_flash.all(axis=None),file=sys.stderr)        
        print("Consistency of boatlock and flash",file=sys.stderr)
        print(boatlock_flash,file=sys.stderr)

    assert boatlock_flash.all(axis=None), "Flashboard must be closed (op) when boatlock is open and vice versa"




    
