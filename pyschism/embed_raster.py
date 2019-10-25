""" Embed finer gridded data in coarser, using curvature flow smoothing to reconcile

    Main function is called embed_fine
"""


import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import scipy.ndimage as cv
from scipy.integrate import odeint
from nodepy import *
import sys
import os.path
from contour_smooth import *


try:
    from osgeo import gdal
    from osgeo.gdalconst import *
    gdal.TermProgress = gdal.TermProgress_nocb
except ImportError:
    import gdal
    from gdalconst import *

    
def embed_raster(input_fg,
                 input_bg,
                 output,
                 nsmooth_init=2,
                 nsmooth_final=1,
                 plot=False,
                 max_time_init=3,
                 max_time_final=1,
                 nstep = 50,
                 report_interval = 1,
                 **kwargs):
    """ Embed a smoother DEM in a coarser
    
        The two inputs and output are filenames. The basic plans is this:
        1. Smooth the fine data enough to resample without aliasing or distortion
        2. Interpolate/resample the result to the coarser mesh
        3. Where the result of 1-2 has good data, replace coarser data
        4. Smooth the final grid lightly to remove kinks/discontinuity
        
        The smoothing is done with contour_smooth2d
    """
    from nodepy import runge_kutta_method as rk
    from nodepy import ivp
    ds_fine = RasterWrapper(input_fg)
    cols = ds_fine.nx
    rows = ds_fine.ny
    nd = ds_fine.no_data
    dx = ds_fine.dx
    dem = ds_fine.dem
    origin = ds_fine.origin

    scales = np.arange(1,nsmooth_init+1)

    #todo: whether this test is legit depends on context. fine for DEM
    if nd < -1e16:
        dem[dem <-1e16] = np.nan
    dem_fine = contour_smooth2d(dem,scales,max_time_init,nstep,report_interval)
    x_fine = origin[0] + dx[0]*(0.5+np.arange(cols))
    y_fine = origin[1] + dx[1]*(0.5+np.arange(rows))
    print("Start interp")
    import scipy.interpolate as si     
    fine_good = np.where(np.isnan(dem_fine),0.,1.)
    
    # this filling is for the interpolator, undone later
    # the nan values will not be used to fill the bg grid
    dem_fine[np.isnan(dem_fine)] = np.nanmean(dem_fine)
    f = si.interp2d(x_fine,y_fine,
                       dem_fine,
                       fill_value=np.nan)
    f2 = si.interp2d(x_fine,y_fine,
                       fine_good,
                       fill_value=np.nan)   
    fg2 = f2(x_fine,y_fine)

    print("End interp")
    
    ds_coarse = RasterWrapper( input_bg)
    
    cols=ds_coarse.nx  
    rows=ds_coarse.ny
    dem_coarse = ds_coarse.dem
    nd = ds_coarse.no_data
    dx_coarse = ds_coarse.dx
    origin_coarse= ds_coarse.origin

    x_coarse = origin_coarse[0] + dx_coarse[0]*(0.5+np.arange(cols))
    y_coarse = origin_coarse[1] + dx_coarse[1]*(0.5+np.arange(rows))
    dem_interp = f(x_coarse,y_coarse,assume_sorted=False)
    dem_interp2 = f2(x_coarse,y_coarse,assume_sorted=False)
    dem_interp[np.less(dem_interp2 , 0.99)] = np.nan

    
    #dem_mixed = dem_interp2
    dem_mixed=np.where(np.isnan(dem_interp[::-1,:]),dem_coarse,dem_interp[::-1,:])

    scales = np.arange(1,nsmooth_final+1)
    dem_final = contour_smooth2d(dem_mixed,scales,max_time_final,nstep,report_interval)

    if plot:
        fig,((ax0,ax1),(ax2,ax3)) = plt.subplots(2,2,sharex=True,sharey=True)    

        levels = [-24,-20,-16,-8,-4,-2,-1,0,1,2,4]
        import matplotlib
        vmin = -24
        vmax = 6
        matplotlib.rcParams['contour.negative_linestyle'] = 'solid'

        ax0.imshow(dem_final,vmin=vmin,vmax=vmax,origin='upper',extent=ds_coarse.extent)
        ax0.set_title("Final 10m")    
        cs0 = ax0.contour(dem_final, levels,
                         origin='upper',
                         colors = 'k',extent=ds_coarse.extent,
                         linewidths=1,antialiased=True)                     

        #ax1.imshow(dem_interp[::-1,:],vmin=-20,vmax=6)
        ax1.set_title("Original 10m DEM")
        ax1.imshow(dem_coarse,vmin=vmin,vmax=vmax,origin='upper',extent=ds_coarse.extent)
        cs1 = ax1.contour(dem_coarse, levels,
                         origin='upper',
                         colors = 'k',extent=ds_coarse.extent,
                         linewidths=1,antialiased=True)
        ax2.set_title("Smoothed 2m DEM")

        ax2.imshow(dem_fine,vmin=vmin,vmax=vmax,origin='upper',extent=ds_fine.extent)
        cs2 = ax2.contour(dem_fine, levels,
                         origin='upper',
                         colors = 'k',extent=ds_fine.extent,
                         linewidths=1,antialiased=True)
        ax3.set_title("Original 2m DEM")
        ax3.imshow(dem,vmin=vmin,vmax=vmax,origin='upper',extent=ds_fine.extent)
        cs3 = ax3.contour(dem, levels,
                         origin='upper',
                         colors = 'k',extent=ds_fine.extent,
                         linewidths=1,antialiased=True)

                         
        #plt.clabel(cs1, inline=1, fontsize=10)                 
        
        plt.show()
    ds_coarse.write_copy(output,dem_final)    
    

def create_arg_parser():
    import schism_yaml 
    import argparse
    import textwrap
    def convert_arg_line_to_args(arg_line):
        for arg in arg_line.split():
            if not arg.strip():
                continue
            yield arg
            
    parser = schism_yaml.ArgumentParserYaml(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      prog = "embed_raster.py", fromfile_prefix_chars="@",
      description= textwrap.dedent(
      """
      Embed coarser gridded data in finer using contour_smooth to avoid discontinuity
      
      """))
    parser.convert_arg_line_to_args = convert_arg_line_to_args    
    parser.add_argument('--input_fg', type=str, help = 'Foreground input file name, tiff format, extent should be covered by background.')
    parser.add_argument('--input_bg', type=str, help = 'Background input file name, tiff format.')
    parser.add_argument('--plot', action = "store_true", help = 'Show diagnostic plot.')    
    parser.add_argument('--output', type=str, help = 'Output file name, tiff format.')    
    parser.add_argument('--nsmooth_init', type = int, default = 1,help="Max smoothing scale applied to fine file before resampling, in multiples of original file pixel size.")
    parser.add_argument('--nsmooth_final', type=int, default = 1, help = 'Max smoothing scale applied to final output file.')    
    parser.add_argument("--max_time_init", type=float, default = 2.0, help="Pseudo time representing the total amount of smoothing for the background raster. This parameter controls the completeness of smoothing, whereas nstep controls the accuracy of it. ")
    parser.add_argument("--max_time_final", type=float, default = 1.0, help="Pseudo time representing the total amount of smoothing for the final smooth.")    
    parser.add_argument("--nstep", type=int, default = 50, help="Number of integration steps between reports. More will give a more accurate integration, but takes more time.")    
    parser.add_argument("--report_interval",type=float, default=1., help="Intermediate interval at which smoothed DEMs will be dumped. So if --max_time is 2.0 and --report_interval is 1. you will get 2 intermediate reports.")

    return parser

if __name__ == '__main__':
    parser = create_arg_parser()
    args = parser.parse_args()
    embed_raster(**vars(args))