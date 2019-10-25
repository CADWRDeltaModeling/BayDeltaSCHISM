""" Functions to cut certain parts in the mesh by cutting lines.
"""
## Author: Kijin Nam, knam@water.ca.gov
## June, 2014
from schism_mesh import read_mesh, write_mesh
import numpy as np
import os

def read_lines(fpath):
    """ Read coordinates of cutting line segments from a plain text file.
        The expected format is:
        x1 y1 x2 y2
        in each line.

        Parameters
        ----------
        fpath
            Name of a file containing coordinates of cutting lines

        Returns
        --------
        list
            List of coordinates of cutting lines
    """
    with open(fpath, 'r') as f:
        lines = list()
        for line in f:
            line = line.strip()
            if len(line) > 0:
                tokens = line.split()
                lines.append(list(map(float, tokens[:4])))
        return lines


def read_lines_from_shapefile(fpath):
    """ Read coordinates of cutting line segments from a ESRI Shapefile
        containing line features.

        Parameters
        ----------
        fpath
            Name of a file containing coordinates of cutting lines

        Returns
        --------
        list
            List of coordinates of cutting lines
    """
    import osgeo.ogr
    driver = osgeo.ogr.GetDriverByName('ESRI Shapefile')
    datasource = driver.Open(fpath, 0)
    if datasource is None:
        print('Could not open ' + fpath)
        raise RuntimeError()
    layer = datasource.GetLayer()
    feature = layer.GetNextFeature()
    lines = list()
    while feature:
        geometry = feature.GetGeometryRef()
        line = geometry.GetPoints()
        lines.append(line)
        feature = layer.GetNextFeature()
    return lines


def cut_mesh(fpath_gr3_in, lines, fpath_gr3_out, cut_side='left'):
    """ Remove elements of a mesh in one side of cutting polyline segments.
        A mesh is read in from a gr3, and a result mesh is written in another
        gr3 file.
        A user needs to be careful that line segments forms a closed division.
        Otherwise, all elements would be deleted.

        Parameters
        ----------
        fpath_gr3_in
            Filename of the input grid in gr3
        lines: array-like
            An array of coordinates of line segments specifying the location
            of cuts
        fpath_gr3_out
            Filename of the output grid in gr3
        cut_side: str, optional
            If cut_side is 'left,' which is default, the left side of cutting
            lines when one sees the second point from the first point of a line
            will be removed.
            If this value is 'right,' the right side will be removed.
    """
    s = read_mesh(fpath_gr3_in)
    lines = np.array(lines).reshape(-1, 4)
    print("{} line(s) to cut found".format(lines.shape[0]))
    if cut_side == 'right':
        # Switch ordering
        lines = np.hstack((lines[:, 2:], lines[:, :2]))
    s.trim_to_left_of_mesh(lines)

    write_mesh(s, fpath_gr3_out)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='A mesh cutting tool.')
    parser.add_argument('gr3_in', type=str,
                        help='a filename of an input grid')
    parser.add_argument('lines', type=str,
                        help='a filename containing lines to cut')
    parser.add_argument('gr3_out', type=str,
                        help='a filename of an output grid')
    parser.add_argument('--cut-side', default='left',
                        help="Which side to cut. If 'right', the right side will be removed.")
    args = parser.parse_args()

    ext = os.path.splitext(args.lines)
    if ext[1] == '.shp':
        lines = read_lines_from_shapefile(args.lines)
    else:
        lines = read_lines(args.lines)
    cut_mesh(args.gr3_in, lines, args.gr3_out, args.cut_side)
