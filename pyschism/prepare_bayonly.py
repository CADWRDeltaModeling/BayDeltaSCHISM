# NOTE: This script is a working version of a use case for Bay-Delta run.
# This script updates inputs as follows:
#
# The list of jobs are:
# 1. Fill up missing land/island boundaries in `hgrid.gr3'.
# 2. Re-order the open boundaries.
# 3. Create source_sink.in.
# 4. Create spatial information such as elev.ic, rough.gr3 and xlsc.gr3.
# 5. Dredge up some part of the domain.
# Woring on this 6. Create an ocean boundary file, elev2D.th
#
# Required inputs files for the job are:
# 1. Source/location file for source_sink.in
# 2. Open boundary ordering file
# 3. Polygon files to create spatial data
#   3.1. Polygons for rough.gr3
#   3.2. Polygons for dredging
# Working on this 4. Tide time history at SF gauge and webtide files (grid and tide files)
#
# Dependacies:
# Rtree python package (On DWR systems, it is already installed in our Python)
# libspatialindex for Rtree (On DWR systems, it can be loaded
#  by 'module load spatialindek)
# pyproj python package (to convert between UTM and Lat/Long)
#
# Last update: Mar 2013
# Author: Kijin Nam, knam@water.ca.gov

from schism_setup import *
import numpy
import subprocess
from datetime import *
import os

## Here are some user inputs such as input file names and time.
## Spatial
input_dir = "../Mesh"
hgrid_in_fname = "bay_delta34.gr3"
upstream_polgyon_fname = "deepening_bayonly.polygons"
output_dir = '../Inputs/bayonly/barotropic'
hgrid_out_fname = "hgrid.gr3"
hgrid_ll_fname = "hgrid.ll"
structure_out_fname = "hydraulics.in"
open_boundary_fname = "open_boundary_bayonly.polygons"
# Order of desired open boundaries. Use names in the hgrid.gr3 file
open_boundary_order = ['Ocean', 'Coyote', 'CCC', 'CCC_Old', \
                       'SWP', 'CVP', 'SJR', 'Calaveras', 'Moke',\
                       'Sacramento', 'Yolo', 'Northbay', 'Napa']
                       # Names of open boundaries in hgrid.gr3
gr3s_one_value = { 'xlsc.gr3':0.1, 'diffmax.gr3':1.0, 'diffmin.gr3':1.0e-6, 
                   'windrot_geo2proj.gr3':0.0, 'elev.ic':0.96,
                   'manning.gr3': 0.025 }
gr3s_polygons = { 'rough.gr3':'rough.polygons',
                  'estuary.gr3':'estuary.polygons',
                  'tvd.gr3':'tvd.polygons'}
transect_in_fname = "flow_xsects.txt"
flux_out_fname = "fluxflag.gr3"

## Temporal
time_start = datetime(2009, 3, 12)
time_end = datetime(2009, 8, 1)
dt = 120.0
sf_tide_in_fpath = "../Data/NOAA/Elev/SanFrancisco_surface.txt"
sf_tide_out_fname = "SF.th"
elev2d_fname = "elev2D.th"
webtide_grid_fname = "ocean.gr3"
webtide_fname = "ocean.ap"

# mesh trimming
sac_line = [615100, 4224445, 615740, 4224075]  # [x1, y1, x2, y2]
sjr_line = [614690, 4212735, 615025, 4212400]
threemile_line = [613983, 4218470, 613735, 4218280]
bigbreak_line1 = [610681, 4208685, 610530, 4208649]
bigbreak_line2 = [611486, 4208944, 611143, 4208804]
bigbreak_line3 = [611952, 4209366, 611541, 4208960]
bigbreak_line4 = [612035, 4209602, 611952, 4209366]


def update_spatial_inputs(s):
    """ Create grid inputs
    """ 
    # Preprocessed the hgrid file

    # Create open boundaries
    s.create_open_boundaries(os.path.join(input_dir, open_boundary_fname))

#     # Ordering up the boundaries
#     s.reorder_open_boundaries(open_boundary_order)
#     # Adopt a new grid
#     new_hgrid_in_fpath = os.path.join(input_dir, new_hgrid_in_fname)
#     s.adopt_new_mesh(new_hgrid_in_fpath)
    
    # Fill the missing land and island boundary information
    print("Filling up missing land and island boundaries...")
    s.mesh.fill_land_and_island_boundarise()
    # Dredging upstearm boundary
    print("Dreding upstearm boundaries...")
    upstream_polgyon_fpath = os.path.join(input_dir, upstream_polgyon_fname)
    s.modify_depth(upstream_polgyon_fpath)
    
    # Write hgrid.gr3
    print("Write up a new hgrid file...")
    hgrid_out_fpath = os.path.join(output_dir, hgrid_out_fname)
    s.write_hgrid(hgrid_out_fpath)
    # Write hgrid.ll
    print("Create a new hgrid.ll file...")
    hgrid_ll_fpath = os.path.join(output_dir, hgrid_ll_fname)
    s.write_hgrid_ll(hgrid_ll_fpath)
    
    # Create GR3 files with one values
    for fname, attribute in gr3s_one_value.items():
        attr_array = numpy.empty(s.mesh.n_nodes())
        attr_array.fill(attribute)
        gr3_fpath = os.path.join(output_dir, fname)
        print("Creating %s..." % fname)
        s.write_hgrid(gr3_fpath, attr_array, False)

    # Create GR3 files with polygons
    for out_fname, polygon_fname in gr3s_polygons.items():
        polygon_fpath = os.path.join(input_dir, polygon_fname)
        gr3_fpath = os.path.join(output_dir, out_fname)
        print("Creating %s..." % out_fname)
        s.create_node_partitioning(gr3_fpath, polygon_fpath)

    # Create fluxflag.gr3
    print("Creating %s..." % flux_out_fname)
    flux_in_fpath = os.path.join(input_dir, transect_in_fname)
    flux_out_fpath = os.path.join(output_dir, flux_out_fname)
    s.create_flux_regions(flux_in_fpath, flux_out_fpath)

    print("Done.")

def update_temporal_inputs(s):
    """ Create temporal inputs. Under development
    """
    # create in interpolated tide file
    sf_tide_out_fpath = os.path.join(output_dir, sf_tide_out_fname)
    s.interpolate_tide(time_start, time_end, dt,
                       sf_tide_in_fpath, sf_tide_out_fpath)
    # Run the fortran code to create elev2D.th
    hgrid_out_fpath = os.path.join(output_dir, hgrid_out_fname)
    webtide_grid_fpath = os.path.join(input_dir, webtide_grid_fname)
    webtide_fpath = os.path.join(input_dir, webtide_fname)
    elev2d_fpath = os.path.join(output_dir, elev2d_fname)
    p = subprocess.Popen(["./gen_elev2D_4_NAVD88", sf_tide_out_fpath, 
                      hgrid_out_fpath, webtide_grid_fpath, webtide_fpath, 
                      elev2d_fpath],
                     stdout = subprocess.PIPE,
                     stderr = subprocess.PIPE)
    return_code = p.wait()
    if return_code != 0:
        for l in p.stdout:
            print(l)
        for l in p.stderr:
            print(l)

def main():
    # Read the grid file to be processed
    s = load_hgrid(os.path.join(input_dir,hgrid_in_fname))

    # Trim the mesh
    lines = [sac_line, sjr_line, threemile_line,
             bigbreak_line2, bigbreak_line3, bigbreak_line4]
    s.trim_to_left_of_mesh(lines)

    s.trim_to_left_of_mesh([bigbreak_line1])

    update_spatial_inputs(s)
#    update_temporal_inputs(s)
    
if __name__ == "__main__":
    main()
