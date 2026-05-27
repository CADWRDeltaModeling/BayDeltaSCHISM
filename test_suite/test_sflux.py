"""Tests to make sure that the sflux netcdf files have consistent dimensions 
and that the base_date in the time variable matches the days offset in the filename.
"""

import pytest
import os
import xarray as xr
import glob
import re
from datetime import datetime


@pytest.mark.prerun
def test_sflux_dimensions(sim_dir, sflux_dirname="sflux"):
    """Reads all netcdf files in sflux folder and checks that nx_grid and ny_grid dimensions are consistent
    
       Loops over all netcdf files matching pattern sflux_***_1.dddd.nc where:
       - *** is one of ["air", "prc", "rad"]
       - dddd is a 4-digit number representing number of days
    
    Verifies that nx_grid and ny_grid dimensions are the same across all files of the same parameter type (air, prc, rad).

    """
    sflux_dir = os.path.join(sim_dir, sflux_dirname)
    
    # Check if sflux directory exists
    assert os.path.isdir(sflux_dir), f"sflux directory not found at {sflux_dir}"
    
    # Pattern for sflux_***_1.dddd.nc files
    pattern = r'sflux_([a-z]+)_1\.(\d{4})\.nc'
    
    # Get all netcdf files in sflux folder
    nc_files = glob.glob(os.path.join(sflux_dir, "*.nc"))
    
    assert len(nc_files) > 0, f"No netcdf files found in {sflux_dir}"
    
    print(f"Found {len(nc_files)} netcdf files in {sflux_dir}")
    
    # Store reference dimensions per parameter type
    reference_dims = {}  # {param_type: (nx_grid, ny_grid, reference_file)}
    
    # Organize files by parameter type
    files_by_param = {}
    for nc_file in nc_files:
        basename = os.path.basename(nc_file)
        match = re.match(pattern, basename)
        if match:
            param_type = match.group(1)
            if param_type not in files_by_param:
                files_by_param[param_type] = []
            files_by_param[param_type].append(nc_file)
    
    # Check dimensions for each parameter type
    for param_type, files in sorted(files_by_param.items()):
        print(f"\nChecking parameter type '{param_type}' ({len(files)} files)")
        
        for nc_file in files:
            try:
                ds = xr.open_dataset(nc_file)
                basename = os.path.basename(nc_file)
                
                # Check if nx_grid and ny_grid dimensions exist
                if 'nx_grid' in ds.dims and 'ny_grid' in ds.dims:
                    nx_grid = ds.dims['nx_grid']
                    ny_grid = ds.dims['ny_grid']
                    
                    print(f"  {basename}: nx_grid={nx_grid}, ny_grid={ny_grid}")
                    
                    # Set reference dimensions from first file of this parameter type
                    if param_type not in reference_dims:
                        reference_dims[param_type] = (nx_grid, ny_grid, basename)
                        print(f"    -> Reference for '{param_type}': nx_grid={nx_grid}, ny_grid={ny_grid}")
                    else:
                        # Check if dimensions match reference for this parameter type
                        ref_nx, ref_ny, ref_file = reference_dims[param_type]
                        assert (
                            nx_grid == ref_nx and ny_grid == ref_ny
                        ), f"File {basename} has nx_grid={nx_grid}, ny_grid={ny_grid}, but reference file {ref_file} has nx_grid={ref_nx}, ny_grid={ref_ny}"
                else:
                    raise AssertionError(f"File {basename} does not have nx_grid and/or ny_grid dimensions")
                
                ds.close()
                
            except Exception as e:
                raise AssertionError(f"Error reading file {os.path.basename(nc_file)}: {str(e)}")
    
    # Print summary by parameter type
    print(f"\nDimension validation summary:")
    for param_type in sorted(reference_dims.keys()):
        nx, ny, ref_file = reference_dims[param_type]
        num_files = len(files_by_param.get(param_type, []))
        print(f"  '{param_type}': {num_files} files with nx_grid={nx}, ny_grid={ny}")

@pytest.mark.prerun
def test_sflux_base_date_consistency(sflux_dir):
    """Check that base_date of time variable in sflux files matches the days offset in filename
    
    Loops over all netcdf files matching pattern sflux_***_1.dddd.nc where:
    - *** is one of ["air", "prc", "rad"]
    - dddd is a 4-digit number representing number of days
    
    Verifies that the days between each file's base_date and the first base_date (from sflux_*_1.0000.nc)
    matches the dddd value in the filename.
    """
    
    # Check if sflux directory exists
    assert os.path.isdir(sflux_dir), f"sflux directory not found at {sflux_dir}"
    
    # Pattern for sflux_***_1.dddd.nc files
    pattern = r'sflux_([a-z]+)_1\.(\d{4})\.nc'
    
    # Get all matching netcdf files
    nc_files = glob.glob(os.path.join(sflux_dir, "sflux_*_1.*.nc"))
    
    # Filter files matching the pattern
    matching_files = []
    for nc_file in nc_files:
        basename = os.path.basename(nc_file)
        match = re.match(pattern, basename)
        if match:
            param_type = match.group(1)
            day_offset = int(match.group(2))
            if param_type in ["air", "prc", "rad"]:
                matching_files.append((nc_file, param_type, day_offset))
    
    assert len(matching_files) > 0, f"No matching sflux_***_1.dddd.nc files found in {sflux_dir}"
    
    print(f"Found {len(matching_files)} matching sflux files")
    
    # Find reference file (0000.nc) for each parameter type
    reference_dates = {}
    
    for nc_file, param_type, day_offset in matching_files:
        if day_offset == 0:
            try:
                ds = xr.open_dataset(nc_file)
                
                # Read base_date from time variable (check coords first, then variables)
                time_var = None
                if 'time' in ds.coords:
                    time_var = ds.coords['time']
                elif 'time' in ds.variables:
                    time_var = ds.variables['time']
                
                if time_var is not None and hasattr(time_var, 'base_date'):
                    base_date_attr = time_var.base_date
                    # base_date is [year, month, day, 0]
                    if hasattr(base_date_attr, '__len__') and len(base_date_attr) >= 3:
                        reference_dates[param_type] = base_date_attr
                        print(f"Reference base_date for {param_type}: {base_date_attr}")
                    else:
                        raise AssertionError(f"base_date attribute in {os.path.basename(nc_file)} has unexpected format: {base_date_attr}")
                else:
                    raise AssertionError(f"Variable 'time' or attribute 'base_date' not found in {os.path.basename(nc_file)}")
                
                ds.close()
            except Exception as e:
                raise AssertionError(f"Error reading reference file {os.path.basename(nc_file)}: {str(e)}")
    
    # Check all files
    for nc_file, param_type, day_offset in matching_files:
        try:
            ds = xr.open_dataset(nc_file)
            
            # Read base_date from time variable (check coords first, then variables)
            time_var = None
            if 'time' in ds.coords:
                time_var = ds.coords['time']
            elif 'time' in ds.variables:
                time_var = ds.variables['time']
            
            if time_var is not None and hasattr(time_var, 'base_date'):
                base_date_attr = time_var.base_date
                
                # base_date is [year, month, day, 0]
                if hasattr(base_date_attr, '__len__') and len(base_date_attr) >= 3:
                    current_date = datetime(int(base_date_attr[0]), int(base_date_attr[1]), int(base_date_attr[2]))
                    
                    if param_type in reference_dates:
                        ref_base_date = reference_dates[param_type]
                        reference_date = datetime(int(ref_base_date[0]), int(ref_base_date[1]), int(ref_base_date[2]))
                        
                        # Calculate days difference
                        days_diff = (current_date - reference_date).days
                        
                        print(f"{os.path.basename(nc_file)}: base_date={base_date_attr}, days_diff={days_diff}, expected={day_offset}")
                        
                        assert days_diff == day_offset, \
                            f"File {os.path.basename(nc_file)}: days difference ({days_diff}) does not match filename offset ({day_offset}). " \
                            f"Current base_date: {current_date.strftime('%Y-%m-%d')}, Reference base_date: {reference_date.strftime('%Y-%m-%d')}"
                    else:
                        raise AssertionError(f"No reference date found for parameter type '{param_type}' (from {os.path.basename(nc_file)})")
                else:
                    raise AssertionError(f"base_date attribute in {os.path.basename(nc_file)} has unexpected format: {base_date_attr}")
            else:
                raise AssertionError(f"Variable 'time' or attribute 'base_date' not found in {os.path.basename(nc_file)}")
            
            ds.close()
            
        except Exception as e:
            raise AssertionError(f"Error checking file {os.path.basename(nc_file)}: {str(e)}")
    
    print(f"All {len(matching_files)} sflux files have consistent base_date with filename offsets")
