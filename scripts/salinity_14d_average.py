from pathlib import Path
import logging
import numpy as np
import xarray as xr
from vtkmodules.vtkCommonCore import VTK_FLOAT
import vtk.util.numpy_support
import suxarray as sx
import datetime as dtm
from schimpy.unit_conversions import *

def salt_average(d0,dt,out):
    logging.basicConfig(level=logging.INFO)
    path_study = Path(out)
    day_start = d0
    day_end = dt
#    day_end = 101
 
    from dask.diagnostics import ProgressBar
    ProgressBar().register()
 
    # Read files lazily
    list_da = []
    for i in range(day_start, day_end + 1):
        logging.info("Reading file info {}...".format(i))
        path_out2d = str(path_study / "outputs/out2d_{}.nc".format(i))
        chunks = None
        ds_out2d = xr.open_mfdataset(path_out2d, mask_and_scale=False, data_vars='minimal', chunks=chunks)
        path_zcoord = str(path_study / "outputs/zCoordinates_{}.nc".format(i))
        ds_zcoord = xr.open_mfdataset(path_zcoord, mask_and_scale=False, data_vars='minimal', chunks=chunks)
        path_var = str(path_study / "outputs/salinity_{}.nc".format(i))
        ds_var = xr.open_mfdataset(path_var, mask_and_scale=False, data_vars='minimal', chunks=chunks)
        ds = xr.merge((ds_out2d, ds_zcoord, ds_var))
     
        # Create a grid object
        grid = sx.Grid(ds)
    
        # Calculate the depth average
        da_depth_averaged_salinity = grid.depth_average('salinity')
        # Calculate the time average
        logging.info("Create a salinity average array...")
        salinity = da_depth_averaged_salinity.mean(dim='time').values
        list_da.append(salinity)	
        
        # Save it to a VTK file
        logging.info("Write it into a VTU...")
        array = vtk.util.numpy_support.numpy_to_vtk(num_array=salinity,
                                      deep=True, array_type=VTK_FLOAT)
        array.SetName('salinity')
        vg = grid.create_vtk_grid()
        vg.GetPointData().AddArray(array)
        sx.write_vtk_grid(vg, "salinity_average_{}.vtu".format(i))

    logging.info("Final averaging...")
    da_salinity = xr.DataArray(np.vstack(list_da), dims=grid.ds.elevation.dims, name='salinity').mean(dim='time')
    da_salinity.to_dataset().to_netcdf("salinity.nc")
    salinity = da_salinity.values
    ec=psu_ec_25c_vec(salinity)
    logging.info("Write it into a VTU...")
    array = vtk.util.numpy_support.numpy_to_vtk(num_array=salinity,
                                  deep=True, array_type=VTK_FLOAT)
    array.SetName('salinity')
    vg = grid.create_vtk_grid()
    vg.GetPointData().AddArray(array)
    sx.write_vtk_grid(vg, "salinity_average_{}_{}.vtu".format(day_start, day_end))
    array = vtk.util.numpy_support.numpy_to_vtk(num_array=ec,
                                  deep=True, array_type=VTK_FLOAT)
    array.SetName('ec')
    vg = grid.create_vtk_grid()
    vg.GetPointData().AddArray(array)
    sx.write_vtk_grid(vg, "ec_average_{}_{}.vtu".format(day_start, day_end))

   
    logging.info("Done.")


if __name__ == '__main__':
     out="/shared/home/*/simulations/edb21_v202302_nobarrier_rev"
     mons=range(6,13)
     year=2021
     model_start=dtm.datetime(year,4,20)
     for mon in mons:
        t0=dtm.datetime(year,mon,1)
        t1=dtm.datetime(year,mon,14)  
        d0=(t0-model_start).days+1
        d1=(t1-model_start).days+1
        salt_average(d0,d1,out)
        print(t0)
     mons=range(1,13)
     year=2022
     
     for mon in mons:
        t0=dtm.datetime(year,mon,1)
        t1=dtm.datetime(year,mon,14)  
        d0=(t0-model_start).days+1
        d1=(t1-model_start).days+1
        salt_average(d0,d1,out)
        print(t0)

