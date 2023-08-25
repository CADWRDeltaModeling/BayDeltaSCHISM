#!/usr/bin/env python
"""
Copy bed fraction from one hotstart from another.
We need to copy/move bed fraction values from a BCG (Bed Composition Generation)
to a cold start.
"""
import click
import numpy as np
import netCDF4 as nc


@click.command()
@click.option('--hotstart_input', required=True,
              help='Original hotstart file to fill with the bed composition')
@click.option('--hotstart_bcg', required=True,
              help='Hotstart file from a BCG run')
@click.option('--hotstart_output', required=True,
              help='Output hotstart file name')
def main(hotstart_input, hotstart_bcg, hotstart_output):
    """
    A script to copy bed fraction data from a hostart file
    (hotstart_bcg) to another hotstart file (hotstart_input)
    and create a new hotstart (hotstart_output).
    The script assumes that the input hotstart file comes with
    bed_frac_ variables.
    """
    fpath_in =  hotstart_input
    fpath_out = hotstart_output
    fpath_bcg = hotstart_bcg

    with nc.Dataset(fpath_in, 'r') as src, \
         nc.Dataset(fpath_bcg, 'r') as bcg, \
         nc.Dataset(fpath_out, "w") as dst:
        # copy attributes
        for name in src.ncattrs():
            dst.setncattr(name, src.getncattr(name))
        # copy dimensions
        print("Copy dimensions...")
        for name, dimension in src.dimensions.items():
            dst.createDimension(
                name,
                (len(dimension) if not dimension.isunlimited()
                    else None))
        # Copy variables
        print("Copy variables...")
        for name, variable in src.variables.items():
            print("Variable: ", name)
            dimensions = variable.dimensions
            dst.createVariable(
                name, variable.datatype, dimensions)
            if name == 'SED3D_bedfrac':
                dst.variables[name][:] = bcg.variables[name][:]
            else:
                dst.variables[name][:] = src.variables[name][:]


if __name__ == '__main__':
    main()

