""" This module contains tools for a smoother for DEMs (currently tiff format) based on curvature flow
    The algorithm is based on one by Malladi and Sethian, and results in a simplification of contours while allowing
    sharp gradients as long as they are persistent. So it is *not* a cure for pressure gradient errors a la Hannah.
    The script shows some artefacts of a time when it wasn't particularly stable and could run out of memory. 
    In particular, the algorithm dumps out intermediate arrays as it goes along and these have to be visualized or saved
    using the appropriate subcommands or functions. Stability is no longer an issue -- it has been good for quite a while.
    Not so sure about memory. I've not tested a big problem yet on a big DEM on 64bit python.
"""


import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt
import scipy.ndimage as cv
from scipy.integrate import odeint
from nodepy import *
import sys
import os.path

try:
    from osgeo import gdal
    from osgeo.gdalconst import *
    gdal.TermProgress = gdal.TermProgress_nocb
except ImportError:
    import gdal
    from gdalconst import *

class RasterWrapper(object):
    def __init__(self,filename): 
        self.filename=filename
        self.ds = gdal.Open( filename, GA_ReadOnly )
        if self.ds is None:
            raise ValueError("DEM is None. Probably file doesn't exist or failed to open")
        gt = self.ds.GetGeoTransform()
        self.nx=self.ds.RasterXSize  
        self.ny=self.ds.RasterYSize     
        self.rb = self.ds.GetRasterBand(1)
        self.dem = self.rb.ReadAsArray()
        self.no_data = self.rb.GetNoDataValue()       
        self.driver = self.ds.GetDriver()
        self.dx = (gt[1],gt[5])
        
        self.origin = (gt[0],gt[3])
        y1 = self.origin[1]
        y2 = self.origin[1]+self.ny*self.dx[1]
        bottom = min(y1,y2)
        top =  max(y1,y2)
        left = self.origin[0]
        right = self.origin[0]+self.nx*self.dx[0]
        self.extent = (left,right,bottom,top)  # left right bottom top
        print(self.extent)

    def write_copy(self,filename,data):
        outdata = self.driver.CreateCopy(filename,self.ds, 0)
        outband = outdata.GetRasterBand(1)
        outband.WriteArray(data)
        outband.FlushCache()
    
def calc_f(t,data,width_shape):
    """ This is the right hand side of the semi-discretized operator (in space) so that it can be integrated in time"""
    width = width_shape[0]
    shp = width_shape[1]
    dem = data.reshape(shp)
    
    tt = t*10
    if abs(tt-np.round(tt))<1e-8:
        print("Eval time = %s width = %s" % (t,width))
    X = np.arange(-width,width+1.,1.)
    Y = np.arange(-width,width+1.,1.)
    X,Y = np.meshgrid(X,Y)
    close = (X*X + Y*Y <=  width*width)
    avefilter = np.zeros_like(X)
    avefilter[close] = 1.0
    avefilter/= avefilter.sum()
    nx = dem.shape[0]
    ny = dem.shape[1]

    gradcent = np.gradient(dem)
    grad_face_x = np.zeros((nx+1,ny),dtype = 'd')
    grad_face_y = np.zeros((nx,ny+1),dtype = 'd')

    grad_face_x[1:nx,:] = dem[1:nx,:] - dem[0:(nx-1),:]
    grad_face_y[:,1:ny] = dem[:,1:ny] - dem[:,0:(ny-1)]
    abs_grad_face_x = np.sqrt( grad_face_x[1:nx,:]**2. + ((gradcent[1][0:(nx-1),:]+gradcent[1][1:nx,:])/2.)**2)
    abs_grad_face_y = np.sqrt( grad_face_y[:,1:ny]**2. + ((gradcent[0][:,0:(ny-1)]+gradcent[0][:,1:ny])/2.)**2)

    
    grad_face_x[1:nx,:] = np.where(abs_grad_face_x > 0.,grad_face_x[1:nx,:]/abs_grad_face_x,0.)
    grad_face_y[:,1:ny] = np.where(abs_grad_face_y > 0.,grad_face_y[:,1:ny]/abs_grad_face_y,0.)

    kappa = grad_face_x[1:(nx+1),:] - grad_face_x[0:(nx+0),:]  + grad_face_y[:,1:(ny+1)] - grad_face_y[:,0:(ny+0)]    

    
    absgrad = np.sqrt(gradcent[0]*gradcent[0] + gradcent[1]*gradcent[1])
    normgradx = np.where(absgrad>0.,gradcent[0]/absgrad,0.)
    normgrady = np.where(absgrad>0.,gradcent[1]/absgrad,0.)
    # set gradient to 0.0 for nan
    normgradx=np.where(np.isnan(normgradx),0.,normgradx)
    normgrady=np.where(np.isnan(normgrady),0.,normgrady)
    
    ave = cv.convolve(dem, avefilter,mode='nearest')
    tangent = [normgrady,-normgradx]


    wt = np.zeros_like(X)
    thresh = np.zeros_like(dem)
    xrange = np.arange(0.5,float(nx),1.0)
    yrange = np.arange(0.5,float(ny),1.0)
    y,x = np.meshgrid(yrange,xrange)    
    epsilon = 1e-4

    
# what if tangent is zero    
    for pdir in [1.0,-1.0]:
        # find the endpoints of the tangent vector of given width
        p0 = [pdir*dir_arr*width for dir_arr in tangent]
        xnew = p0[0]+  x
        ynew = p0[1] + y
        
        # take care of special cases where the end point exceeds the mesh (0,nx) x (0,ny)
        # this is done by finding where the segment intersects the boundary and using that cell
        bad = xnew < 0        
        ynew[bad] = np.minimum(ny-epsilon,np.maximum(ynew[bad] + -pdir*(tangent[1][bad]/tangent[0][bad])*x[bad],0.))
        xnew[bad] = 0
        bad = xnew > nx - epsilon
        ynew[bad] = np.minimum(ny-epsilon,np.maximum(ynew[bad] + -pdir*(tangent[1][bad]/tangent[0][bad])*(nx-x[bad]),0.))
        xnew[bad] = nx-0.5

        bad = ynew < 0        
        xnew[bad] = np.minimum(nx-epsilon,np.maximum(xnew[bad] + -pdir*(tangent[0][bad]/tangent[1][bad])*y[bad],0.))
        ynew[bad] = 0.
        
        bad = ynew > ny - epsilon
        xnew[bad] = np.minimum(nx-epsilon,np.maximum(xnew[bad] + -pdir*(tangent[0][bad]/tangent[1][bad])*(ny-y[bad]),0.))
        ynew[bad] = ny - 0.5
        
        inew0 = xnew.astype("i")
        jnew0 = ynew.astype("i")
        thresh += 0.5*dem[inew0,jnew0]
    f = np.where(ave<thresh,np.where(kappa > 0.0,kappa,0.),np.where(kappa<0.0,kappa,0.))      
    return f.flatten()
    
def contour_smooth(input,scales,max_time,nstep,report_interval,fill_val=2.,**kwargs):
    """ Driver function for smoothing a DEM"""
    print("input: %s" % input)
    ds = RasterWrapper(input)
    outpathsplit = os.path.splitext(input)
    outfile = outpathsplit[0]+"_smooth"+outpathsplit[1]
    print("Out: %s" % outfile)
    cols=ds.nx  
    rows=ds.ny
    dem = ds.dem
    nd = ds.no_data
    print("No data value: %s" % nd)
    #dem[np.equals(dem,nd)] = fill_val
    dem_shape = dem.shape
    print("DEM shape: %s %s" % dem_shape)	
    smoothed_dem = contour_smooth2d(dem,scales,max_time,nstep,report_interval)
    ds.write_copy(outfile,smoothed_dem)
    
def contour_smooth2d(dem,scales,max_time,nstep,report_interval):  
    demold = dem.copy()
    dem_shape = dem.shape
    mask_good = ~np.isnan(demold)
    demold[~mask_good] = np.nanmean(demold)
    
    from nodepy import runge_kutta_method as rk
    from nodepy import ivp
    rkc = rk.RKC2(4,0.01)
    np.save("smoothed_0_0", dem)
    t = 0. 
    for iscale in scales:
        t=0.0
        itime = 0
        while t < max_time:
            stop_time = min (max_time, t + report_interval)
            prob = ivp.IVP(f=calc_f,u0=dem.flatten(),T=stop_time)
            out = rkc(prob,t0=t,N=nstep,x=(iscale,dem_shape))
            t = stop_time            
            dem = out[1][-1].reshape(dem_shape)
            differ = dem[mask_good] - demold[mask_good]
            diffinf = np.amax(np.abs(differ))
            print("diff: %s %s" % (np.sqrt((differ*differ).mean()),diffinf))
            demold = dem
            itime = itime + 1
            np.save("smoothed_%s_%s" % (iscale,itime),dem)

    dem[~mask_good]=np.nan
    return dem
    
def view_smooth(file0,file1,levels,vmin,vmax,**kwargs): 
    """ View the dumped files to graphically explore smoothing progress""" 
    import sys
    import numpy as np
    import matplotlib.pyplot as plt

    print(levels)
    dem0 = np.load(file0)
    dem1 = np.load(file1)

    fig, (ax0,ax1) = plt.subplots(1,2,sharex=True,sharey=True,figsize=(16,6))
      
    im0 =ax0.imshow(dem0,vmin=vmin,vmax=vmax)
    cs0 = ax0.contour(dem0, levels,
                     origin='lower',
                     colors = 'k',
                     linewidths=1,antialiased=True)

    #fig.colorbar(im0)
    im1 = ax1.imshow(dem1,vmin=vmin,vmax=vmax)
    
    cs1 = ax1.contour(dem1, levels,
                     origin='lower',
                     colors = 'k',
                     linewidths=1,antialiased=True)
    plt.clabel(cs1, inline=1, fontsize=10)           
    #fig.colorbar(im1)    
    plt.show()


def save_smooth(dumpfile,original,outfile,**kwargs):
    print("Saving")
    print("Original DEM file: %s" % original)
    print("Array dump file: %s" % dumpfile)
    print("Output: %s" % outfile)

    
    ds = gdal.Open( original, GA_ReadOnly )
    gt = ds.GetGeoTransform()
    cols=ds.RasterXSize  
    rows=ds.RasterYSize     
    rb = ds.GetRasterBand(1)
    demimg = rb.ReadAsArray()  #[:,104:]
    nd = rb.GetNoDataValue()
    driver = ds.GetDriver()


    dem = np.load(dumpfile)
    if (dem.shape != demimg.shape):
        raise ValueError("Dumpfile %s, %sx and original %s, %s do not appear to be the same size." % (dumpfile,dem.shape,original,demimg.shape))
    outdata = driver.CreateCopy(outfile,ds, 0)
    outband = outdata.GetRasterBand(1)
    outband.WriteArray(dem)
    outband.FlushCache()
    outdata=None
    ds = None        

    


    
def create_arg_parser():
    import argparse
    import textwrap
    def convert_arg_line_to_args(arg_line):
        for arg in arg_line.split():
            if not arg.strip():
                continue
            yield arg
            
    parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      prog = "contour_smooth.py", fromfile_prefix_chars="@",
      description= textwrap.dedent(
      """
      Uses the min-max curvature flow algorithm of Malladi and Sethian to simplify DEM topograph
      The script requires a subcommand like: $ contour_smooth.py smooth
      The most basic subcommand is "smooth". 
      Given limited efficiency at the moment, the script is generally run on a small area 
      and dumps intermediate points in the processing as numpy arrays so you can 
      view the differences using the contour_smooth.py view subcommand.
      You can  get subject-specific help on a subcommand by typing
      $ model_time.py subcommand --help
      """))
    parser.convert_arg_line_to_args = convert_arg_line_to_args
    
    subparsers = parser.add_subparsers(title='subcommands',help='sub-commands indicating the particular action required. ',dest='subcommand')
    
    parser_smooth = subparsers.add_parser('smooth', help='Smooth the input DEM.') 
    parser_smooth.add_argument('--input', type=str, help = 'Input file name, file in tiff format.') 
    parser_smooth.add_argument('--scales', type = int, nargs='*', default = [1,2],help="Scales (in multiples of DEM side length) over which to smooth. The sequence [1,2,3,4] is an example, where the smoothing is gradually introduced at 10m, 20m, 30m and 40m for a 10m DEM.")
    parser_smooth.add_argument('--nstep', type=int, default=40, help="number of pseudo time steps to resolve integration. Default of 160 is recommended.")
    parser_smooth.add_argument("--max_time", type=float, default = 4.0, help="Pseudo time representing final time step. 2.0 is the default.")
    parser_smooth.add_argument("--report_interval",type=float, default=1.0, help="Intermediate interval at which integration will be segmented and smoothed DEMs will be dumped. So if --max_time is 2.0 and --report_interval is 0.1 you will get 20 intermediate reports.")
    parser_smooth.set_defaults(func = contour_smooth)

    parser_view = subparsers.add_parser('view', help='View two versions of the smoothed DEM based on their .npy dump.') 
    parser_view.add_argument('file0', type=str, help = 'First file in .npy format.')
    parser_view.add_argument('file1', type=str, help = 'Second file in .npy format.')
    parser_view.add_argument('--levels', type = float, nargs='*', default = [-4,-3,-2,-1,0,1],help="Contour levels")
    parser_view.add_argument('--vmin', type = float, default = -6.0,help="Minimum elevation in color bar")
    parser_view.add_argument('--vmax', type = float, default =  4.0,help="Maximum elevation in color bar")

    parser_view.set_defaults(func = view_smooth)

    parser_save = subparsers.add_parser('save', help='save dumped DEM based on .npy dump and the original DEM it came from.') 
    
    parser_save.add_argument('--dumpfile', type=str, help = 'Dump file from smoothing (npy format)')
    parser_save.add_argument('--original', type=str, help = 'Original DEM (GeoTiff).')
    parser_save.add_argument('--outfile', type=str, help = 'Output file that will be saved (GeoTiff format).')
    parser_save.set_defaults(func = save_smooth)
    return parser
    

if __name__ == '__main__':
    parser = create_arg_parser()
    args = parser.parse_args()
    func = args.func
    func(**vars(args))
