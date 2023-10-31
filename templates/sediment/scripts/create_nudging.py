# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22, 2022
Example script to create SCHISM nudging files and 
visualize the results.
@author: zzhang
"""

from schimpy import nudging
from schimpy.schism_mesh import read_mesh
import xarray as xr
import matplotlib.pyplot as plt

yaml_fn = 'nudge_obs_roms.yaml'

nudging = nudging.nudging(yaml_fn,proj4 ='EPSG:32610')
nudging.read_yaml()
nudging.create_nudging()