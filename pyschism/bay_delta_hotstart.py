#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
""" A script to create a hotstart.in for the Bay-Delta
"""

from hotstart_generator import (HotstartGenerator,
                                RegionalInitializer,
                                NearestNeighborInitializer,
                                init_logger,
                                read_stations, read_station_data)
from schism_mesh import read_mesh
from schism_polygon import read_polygons
import os


def create_arg_parser():
    """ Create an ArgumentParser for Bay-Delta hotsart
    """
    import schism_yaml
    parser = schism_yaml.ArgumentParserYaml()
    parser.add_argument('--hgrid',
                        default='hgrid.gr3',
                        help="Horizontal grid")
    parser.add_argument('--vgrid',
                        default='vgrid.in',
                        help="Vertical grid")
    parser.add_argument('--elev',
                        help="Elevation")
    parser.add_argument('--usgs_station', required=True,
                        help="USGS cruise station file")
    parser.add_argument('--usgs_data', required=True,
                        help="USGS synoptic cruise data")
    parser.add_argument('--cdec_station',
                        help="CDEC station file")
    parser.add_argument('--cdec_data',
                        help="CDEC data")
    parser.add_argument('--estuary',
                        default='estuary.yaml',
                        help="polygon file that defines regions")
    parser.add_argument('--delta_salt',
                        type=float,
                        default=0.1,
                        help="Salinity value of the Delta area (PSU)")
    parser.add_argument('--ocean_salt',
                        type=float,
                        default=33.5,
                        help="Ocean salinity value (PSU)")
    parser.add_argument('--hotstart',
                        default='hotstart.in',
                        help="hotstart output file name")
    return parser


def process_cruise_data(cruise, constituent):
    """
    Collect and process what we need

    Returns
    -------
    dict
        a dictionary with two keys, 'header' and 'data'.
        The value corresponding to 'header' key is list of column items.
        The value corresponding to 'data' key is a dictionary whose key
        is station_id and value is a list of values.

        The structure of this data is not convenient or easy to understand.
        It will be updated later.
    """
    processed = {}
    idx_id = cruise['header'].index('Station Number')
    header = [field for field in ('depth', constituent)
              if field in cruise['header']]
    idx_data = [cruise['header'].index(field) for field in header]
    for cast in cruise['data']:
        station_id = cast[idx_id]
        record = [float(cast[i]) for i in idx_data]
        cast_of_station = processed.get(station_id)
        if cast_of_station is None:
            processed[station_id] = [record]
        else:
            processed[station_id].append(record)
    # Sort based on depth
    for k in processed:
        processed[k] = sorted(processed[k])
    return {'header': header, 'data': processed}


def bay_delta_hotstart_with_cdec_stations(args):
    """ Create a hotstart file with USGS cruise data and CDEC data
        If CDEC data is not given, a constant salinity is set

        Parameters
        ----------
        args: namespace
            command line arguments parsed by argparse
    """
    logger = init_logger('bay_delta_hotstart')
    generator = HotstartGenerator(logger=logger)
    fpath_mesh = args.hgrid
    fpath_vgrid = args.vgrid
    fpath_elev_polygons = args.elev
    fpath_usgs_cruise = args.usgs_data
    fpath_usgs_cruise_stations = args.usgs_station
    fpath_cdec_data = args.cdec_data
    fpath_cdec_stations = args.cdec_station
    fpath_estuary_polygons = args.estuary
    fpath_hotstart = args.hotstart
    polygons_estuary = read_polygons(fpath_estuary_polygons)
    if fpath_elev_polygons is not None:
        polygons_elev = read_polygons(fpath_elev_polygons)
    else:
        polygons_elev = None
    usgs_stations = read_stations(fpath_usgs_cruise_stations)
    usgs_data = read_station_data(fpath_usgs_cruise)
    for row in usgs_data:
        if 'station number' in row:
            row['id'] = row['station number']
            del row['station number']
    if fpath_cdec_stations is not None:
        cdec_stations = read_stations(fpath_cdec_stations)
    else:
        cdec_stations = None
    if fpath_cdec_data is not None:
        cdec_data = read_station_data(fpath_cdec_data)
    else:
        cdec_data = None

    # Load mesh information
    if not os.path.exists(fpath_mesh):
        logger.error("A mesh file not found: %s", fpath_mesh)
        raise ValueError("A mesh file not found")
    if not os.path.exists(fpath_vgrid):
        logger.error("A vertical mesh file not found: %s", fpath_vgrid)
        raise ValueError("A vertical mesh file not found")
    logger.info("Reading a mesh...")
    mesh = read_mesh(fpath_mesh, fpath_vgrid)

    logger.info("Setting up initializers...")
    # Salinity
    ocean_salt = args.ocean_salt
    if cdec_data is not None:
        generator.gen_salt = \
            RegionalInitializer(mesh, polygons_estuary,
                                {'default': ocean_salt,
                                 'bay': NearestNeighborInitializer(mesh, usgs_stations, usgs_data, 'salinity'),
                                 'delta': NearestNeighborInitializer(mesh, cdec_stations, cdec_data, 'salinity'),
                                })
    else:
        delta_salt = args.delta_salt
        generator.gen_salt = \
            RegionalInitializer(mesh, polygons_estuary,
                                {'default': ocean_salt,
                                 'bay': NearestNeighborInitializer(mesh, usgs_stations, usgs_data, 'salinity'),
                                 'delta': delta_salt
                                })

    # Temperature
    generator.gen_temp = RegionalInitializer(mesh, polygons_estuary,
                                             {'default': 12.,
                                              'bay': NearestNeighborInitializer(mesh, usgs_stations, usgs_data, 'temperature'),
                                              'delta': 10.5
                                             })
    # Elevation
    if polygons_elev is not None:
        generator.gen_elev = RegionalInitializer(mesh, polygons_elev,
                                                 {'default': 0.96,
                                                  'ccfb':  0.525})
    else:
        generator.gen_elev = None

    # Create hotstart file
    logger.info("Start creating a hotstart file...")
    generator.create_hotstart(mesh, fpath_hotstart)


def main():
    """ Main function for command line run
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    # Read USGS Data
    bay_delta_hotstart_with_cdec_stations(args)


if __name__ == "__main__":
    main()
