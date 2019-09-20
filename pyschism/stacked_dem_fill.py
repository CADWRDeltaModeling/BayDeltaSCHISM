'''
Module contains routines to fill elevation (or other scalar) values at points from a prioritized list of rasters

Depends on GDAL for loading values. GDAL is easily installed with no tertiary dependencies.

The module requires Python 2.7
'''

try:
    from osgeo import gdal
    from osgeo.gdalconst import *
    gdal.TermProgress = gdal.TermProgress_nocb
except ImportError:
    import gdal
    from gdalconst import *

import numpy as np
import sys
import os
DEFAULT_NA_FILL = 2.0


def stacked_dem_fill(files, points, values=None, negate=False, require_all=True, na_fill=None):
    '''
    Fill values at an array of points using bilinear interpolation from a prioritized stack of dems.
    This routine controls prioritization of the dems, gradually filling points that are still marked "nan"

    files:  list of files. Existence is checked and ValueError for bad file
    points: this is a numpy array of points, nrow = # points and ncol = 2 (x,y).
    values: values at each point
    negate:      if True, values will be inverted (from elevation to depth)
    require_all: if True, a ValueError is raised if the list of DEMs does not cover all the points. In either case (True/False)
                 a file is created or overwritten ("dem_misses.txt") that will show all the misses.
    na_fill:     value to substitute at the end for values that are NA after all DEMs are processed.
                If require_all = True na_fill must be None
    '''
    if values is None:
        values = np.full(points.shape[0], np.nan)
    else:
        values = np.array(values, copy=True)
    points = points[:, :2]
    if require_all and na_fill:
        raise ValueError("Incompatible: require_all and na_fill")
    for infile in files:
        if not os.path.exists(infile):
            raise ValueError("File does not exist: %s" % infile)
        print("Using DEM: %s" % infile)
        indataset = gdal.Open(infile, GA_ReadOnly)
        gt = indataset.GetGeoTransform()
        rb = indataset.GetRasterBand(1)
        dem = rb.ReadAsArray()
        nd = rb.GetNoDataValue()
        if not (nd is None):
            dem[dem == nd] = np.nan
        filled = bilinear(points[np.isnan(values)], gt, dem)
        filled[filled < -20000] = np.nan
        values[np.isnan(values)] = filled
        indataset = None
        dem = None
        rb = None

    if negate:
        values = np.negative(values)
    if any(np.isnan(values)):
        f = open("dem_misses.txt", "w")
        for p in points[np.isnan(values)]:
            f.write("%s,%s\n" % tuple(p))
            message = "DEMs provided do not cover all the points. See file dem_misses.txt for locations"
        f.close()
        if require_all:
            raise ValueError(message)
        else:
            print(message)
    if na_fill is not None:
        values[np.isnan(values)] = na_fill
    return values


# =============================================================================
def Usage():
    print('Usage: stacked_dem_fill.py demfilelist pointlist')
    sys.exit(1)

# =============================================================================

# =============================================================================


def ParseType(type):
    gdal_dt = gdal.GetDataTypeByName(type)
    if gdal_dt is GDT_Unknown:
        gdal_dt = GDT_Byte
    return gdal_dt

# =============================================================================


def bilinear(points, gt, raster):
    '''Bilinear interpolated point at (px, py) using data on raster
       points: npoint x 3 array of (x,y,z points)
       gt: geotransform information from gdal
       raster: the data
    '''
    px = points[:, 0]
    py = points[:, 1]
    ny, nx = raster.shape

    # Half raster element widths
    hx = gt[1]/2.0
    hy = gt[5]/2.0
    # Calculate raster lower bound indices from point
    fx = (px - (gt[0] + hx))/gt[1]
    fy = (py - (gt[3] + hy))/gt[5]
    ix1 = np.floor(fx).astype(int)
    iy1 = np.floor(fy).astype(int)

    # Special case where point is on upper bounds
    #ix1=np.where(fx == float(nx - 1), ix1 - 1, ix1)
    #iy1=np.where(fy == float(ny - 1), iy1 -1, iy1)
    # Upper bound indices on raster
    ix2 = ix1 + 1
    iy2 = iy1 + 1

    # Test array bounds to ensure point is within raster midpoints
    inbounds = (ix1 >= 0) & (iy1 >= 0) & (ix2 <= nx - 1) & (iy2 <= ny - 1)

    #    return no_data
    inboundx = points[inbounds, 0]
    inboundy = points[inbounds, 1]

    ix1 = ix1[inbounds]
    ix2 = ix2[inbounds]
    iy1 = iy1[inbounds]
    iy2 = iy2[inbounds]

    # nearx = (np.abs(inboundx - 6.25143225e+005) <
    #          1.) & (np.abs(inboundy-4.20178364e+006) < 1.)

    # Calculate differences from point to bounding raster midpoints
    dx1 = inboundx - (gt[0] + ix1*gt[1] + hx)
    dy1 = inboundy - (gt[3] + iy1*gt[5] + hy)
    dx2 = (gt[0] + ix2*gt[1] + hx) - inboundx
    dy2 = (gt[3] + iy2*gt[5] + hy) - inboundy
    # Use the differences to weigh the four raster values
    div = gt[1]*gt[5]

    res = np.zeros_like(points[:, 0])
    res[:] = np.nan
    res[inbounds] = (raster[iy1, ix1]*dx2*dy2/div +
                     raster[iy1, ix2]*dx1*dy2/div +
                     raster[iy2, ix1]*dx2*dy1/div +
                     raster[iy2, ix2]*dx1*dy1/div)
    ix1 = None
    ix2 = None
    iy1 = None
    iy2 = None

    return res


# =================================================================
def test_main():
    points = np.zeros((4, 3), dtype=np.float64)
    points[0, :] = (546679, 4184973, np.nan)
    points[1, :] = (542385, 4184978, np.nan)
    points[2:, ] = (616877, 4226454, np.nan)
    points[3:, ] = (816877, 4226454, np.nan)

    print(stacked_dem_fill(["bay_delta_mini.tif", "bay_delta_west.tif", "bay_delta_east.tif"], points[:, :2], points[:, 2]))


def filelist_main(demlistfile, pointlistfile, sep=""):
    '''
    higher level driver routine that parses the names of the DEMs from demfilelist
    points ( x,y or x,y,z ) from pointlistfile
    '''

    filelist = [f.strip()
                for f in open(demlistfile, "r").readlines() if f and len(f) > 1]
    bad_files = [f for f in filelist if not os.path.exists(f)]
    if len(bad_files) > 0:
        for fname in bad_files:
            print("Does not exist: %s " % fname)
        raise ValueError("Some file(s) not found")
    points = np.loadtxt(pointlistfile, delimiter=sep).copy()
    print(points)
    pshape = points.shape
    if pshape[1] == 2:
        z = np.zeros((points.shape[0], 1), dtype=np.float64)
        points = np.hstack((points, z))
        # points.resize((pshape[0],3),refcheck=False)
    points[:, 2] = np.nan
    print(points)
    points = stacked_dem_fill(filelist, points[:, :2], points[:, 2])
    print(points)
    return points


def fill_2dm(infile, outfile, files,na_fill=DEFAULT_NA_FILL):
    import string
    print("Filling elevations in %s and writing to %s" % (infile, outfile))
    f = open(infile, 'r')
    all_lines = f.readlines()
    f.close()
    firstndx = next(
        (i for i, v in enumerate(all_lines) if v.startswith("ND")), -1)
    endndx = next((i for i, v in enumerate(
        all_lines[firstndx:]) if not v.startswith("ND")), -1) + firstndx
    pts = np.array([[float(x) for x in string.split(s.strip())[2:5]]
                    for s in all_lines[firstndx: endndx]])
    pts[:, 2] = np.nan
    values = stacked_dem_fill(files, pts[:, :2], pts[:, 2],
                              require_all=False, na_fill=na_fill)

    all_lines[firstndx:endndx] = ("ND %i  %18.8f %18.8f  %18.8f\n" %
                                  ((i+1), pt[0], pt[1], val)
                                  for i, (pt, val) in enumerate(zip(pts, values)))
    fout = open(outfile, "w")
    for line in all_lines:
        fout.write(line)
    return None


def fill_gr3(infile, outfile, files, elev2depth=True,na_fill=DEFAULT_NA_FILL):
    import string
    import math
    print("Filling elevations in %s and writing to %s" % (infile, outfile))
    f = open(infile, 'r')
    all_lines = f.readlines()
    f.close()
    # read the first line of text and convert nelement and nnode to integers
    nelement, nnode = [int(x) for x in all_lines[1].split()[0:2]]
    firstndx = 2
    stopndx = nnode+2
    pts = np.array([[float(x) for x in string.split(s.strip())[1:4]]
                    for s in all_lines[firstndx:stopndx]])
    pts[:, 2] = np.nan
    values = stacked_dem_fill(files, pts[:, :2], pts[:, 2],
                              require_all=False, na_fill=na_fill, negate=elev2depth)
    padding = 2
    maxnum = int(math.log10(max(nelement, nnode))) + padding
    # ifmt = "%" + ("%ii" % maxnum)
    ifmtj = "%-" + ("%ii" % maxnum)
    ffmt = "%18.8f"
    nfmt = ifmtj + ffmt*3 + "\n"

    all_lines[firstndx:stopndx] = (
        nfmt % ((i+1), pt[0], pt[1], val) for i, (pt, val) in enumerate(zip(pts, values)))

    fout = open(outfile, "w")
    for line in all_lines:
        fout.write(line)
    return None


def create_arg_parser():
    import argparse
    parser = argparse.ArgumentParser(
        description='Fill node elevations in a *.2dm SMS mesh or gr3 file using a prioritized list of DEMs.')
    parser.add_argument(
        dest='filename', default=None, help='name of 2dm or gr3 file')
    parser.add_argument(
        'demfile', default=None, help='file containing list of DEMs. These can be in any form that gdal accepts, which includes ESRI ascii format and GeoTiffs')
    parser.add_argument('--elev2depth', action='store_true', default=False,
                        help='Convert elevation to depth by flipping sign. This is typical when using gr3 format, less so with 2dm.')
    parser.add_argument('--fill', default=DEFAULT_NA_FILL,
                        help='Fill value for areas not covered by supplied rasters.')                    
    return parser


def main():
    import shutil
    parser = create_arg_parser()
    args = parser.parse_args()
    infile = args.filename
    bakfile = infile + ".bak"
    print("Backing up file to %s" % bakfile)
    shutil.copyfile(infile, bakfile)
    demlistfile = args.demfile
 
    if demlistfile.endswith('.txt'):
        files = [x.strip() for x in open(demlistfile, "r").readlines()
                 if x and len(x) > 1 and not x.startswith("#")]
    elif demlistfile.endswith('.yaml'):
        import yaml
        with open(demlistfile, 'r') as f:
            files = yaml.load(f)
    else:
        raise ValueError("Not supported DEM list file extension")

    elev2depth = args.elev2depth
    na_fill = args.fill       
    if infile.endswith(".2dm"):
        if elev2depth:
            print("Warning: --elev2depth is an unusual option for 2dm files")
        fill_2dm(bakfile, infile, files, na_fill=na_fill)
    elif infile.endswith(".gr3"):
        if not elev2depth:
            print("Warning: omitting --elev2depth is an unusual option for gr3 files")
        fill_gr3(bakfile, infile, files, elev2depth, na_fill=na_fill)
    else:
        raise ValueError(
            "Input file format not recognized (no gr3 or 2dm extension")

if __name__ == "__main__":
    main()
