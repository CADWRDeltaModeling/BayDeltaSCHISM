#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Driver module to prepares input files for a SCHISM run.
Example jobs in this pre-processing are:
  1. Fill up missing land/island boundaries in `hgrid.gr3'.
  2. Re-order the open boundaries.
  3. Create source_sink.in and hydraulics.in
  4. Create spatial information such as elev.ic, rough.gr3 and xlsc.gr3.
  5. Dredge up some part of the domain.
  6. Create an ocean boundary file, elev2D.th
"""

from schism_setup import create_schism_setup, check_and_suggest
from grid_opt import GridOptimizer
from stacked_dem_fill import stacked_dem_fill
import schism_yaml
import numpy as np
import subprocess
import os
import argparse
import logging


def create_arg_parser():
    """ Create ArgumentParser
    """
    parser = argparse.ArgumentParser(description='Prepare SCHISM input files.')
    parser.add_argument(dest='main_inputfile', default=None,
                        help='main input file name')
    return parser


def create_hgrid(s, inputs, logger):
    """ Preprocessed the hgrid file
    """
    section_name = 'mesh'
    section = inputs.get(section_name)
    if section is not None:
        open_boundaries = section.get('open_boundaries')
        if open_boundaries is not None:
            logger.info("Processing open boundaries...")
            check_and_suggest(open_boundaries, ('linestrings',))
            s.create_open_boundaries(open_boundaries)

            # Fill the missing land and island boundary information
            logger.info("Filling missing land and island boundaries...")
            s.mesh.fill_land_and_island_boundaries()
        # Second, Mesh optimization
        option_name = 'depth_optimization'

        # if option_name in section.keys():
        opt_params = section.get(option_name)
        default_depth_for_missing_dem = 2.0
        if opt_params is not None:
            dem_list = section.get('dem_list')
            if dem_list is None:
                raise ValueError(
                    "dem_list must be provided for the mesh optimization")
            expected_items = ('damp',
                              'damp_shoreline',
                              'face_coeff',
                              'volume_coeff')
            check_and_suggest(opt_params, expected_items)
            logger.info("Start optimizing the mesh...")
            optimizer = GridOptimizer(mesh=s.mesh,
                                      demfiles=dem_list,
                                      na_fill=default_depth_for_missing_dem,
                                      logger=logger)
            optimized_elevation = optimizer.optimize(opt_params)
            s.mesh.nodes[:, 2] = np.negative(optimized_elevation)
        else:
            dem_list = section.get('dem_list')
            if dem_list is not None:
                s.mesh.nodes[:, 2] = np.negative(stacked_dem_fill(dem_list,
                                                                  s.mesh.nodes[:, :2],
                                                                  require_all=False,
                                                                  na_fill=default_depth_for_missing_dem))

        # Write hgrid.gr3
        option_name = 'gr3_outputfile'
        if option_name in section:
            logger.info("Writing up a new hgrid file...")
            hgrid_out_fpath = os.path.expanduser(section[option_name])
            s.write_hgrid(hgrid_out_fpath)

        # Write hgrid.ll
        option_name = 'll_outputfile'
        if option_name in section:
            logger.info("Creating a new hgrid.ll file...")
            hgrid_ll_fpath = os.path.expanduser(section[option_name])
            s.write_hgrid_ll(hgrid_ll_fpath)


def create_source_sink(s, inputs, logger):
    """ Create source_sink.in
    """
    dict_ss = inputs.get('sources_sinks')
    if dict_ss is None:
        return
    logger.info("Processing sources/sinks inputs...")
    expected_items = ('sources', 'sinks', 'outputfile')
    check_and_suggest(dict_ss, expected_items)
    sources = dict_ss.get('sources')
    sources_sinks = {}
    if sources is not None:
        sources_sinks['sources'] = sources
    sinks = dict_ss.get('sinks')
    if sinks is not None:
        sources_sinks['sinks'] = sinks
    fname = dict_ss.get('outputfile')
    if fname is not None:
        fname = os.path.expanduser(fname)
        logger.info("Creating %s..." % fname)
        s.create_source_sink_in(sources_sinks, fname)


def create_gr3_with_polygons(s, inputs, logger):
    """ Create GR3 files with polygons
    """
    dict_gr3 = inputs.get('gr3')
    if dict_gr3 is None:
        return
    logger.info("Processing gr3 outputs...")
    expected_items = ('polygons', 'default')
    for fname, item in dict_gr3.items():
        check_and_suggest(item, expected_items)
        polygons = item.get('polygons', [])
        if polygons is not None:
            polygon_items = ('name', 'vertices', 'type', 'attribute')
            for polygon in polygons:
                check_and_suggest(polygon, polygon_items)
    for fname, item in dict_gr3.items():
        if fname is None:
            logger.warning("No filename is given in one of gr3")
            continue
        fname = os.path.expanduser(fname)
        polygons = item.get('polygons', [])
        default = item.get('default')
        logger.info("Creating %s..." % fname)
        s.create_node_partitioning(fname, polygons, default)


def create_prop_with_polygons(s, inputs, logger):
    """ Create prop files with polygons
    """
    dict_prop = inputs.get('prop')
    if dict_prop is None:
        return
    logger.info("Processing prop outputs...")
    expected_items = ('default', 'polygons')
    for fname, item in dict_prop.items():
        check_and_suggest(item, expected_items)
        polygons = item.get('polygons', [])
        if polygons is not None:
            polygon_items = ('name', 'vertices', 'type', 'attribute')
            for polygon in polygons:
                check_and_suggest(polygon, polygon_items)
    for fname, item in dict_prop.items():
        if fname is None:
            logger.warning("No filename is given in one of prop")
            continue
        fname = os.path.expanduser(fname)
        polygons = item.get('polygons', [])
        default = item.get('default')
        logger.info("Creating %s..." % fname)
        s.create_prop_partitioning(fname, polygons, default)


def create_structures(s, inputs, logger):
    """ Create a structure file
    """
    dict_struct = inputs.get('hydraulics')
    if dict_struct is None:
        return
    logger.info("Processing structures...")
    expected_items = ('nudging', 'structures', 'outputfile')
    check_and_suggest(dict_struct, expected_items)
    structures = dict_struct.get('structures')
    if structures is None:
        logger.error("No structures in hydraulics section")
        raise ValueError("No structures in hydraulics section")
    structure_items = ('name', 'type', 'end_points',
                       'configuration', 'reference')
    configuration_items = ('n_duplicates', 'elevation', 'width', 'height',
                           'radius', 'coefficient',
                           'op_downstream', 'op_upstream',
                           'use_time_series', 'coefficient_height',
                           'culvert_n_duplicates', 
                           'culvert_elevation', 'culvert_radius',
                           'culvert_coefficient',
                           'culvert_op_downstream', 'culvert_op_upstream')
    nudging = dict_struct.get('nudging')
    for structure in structures:
        check_and_suggest(structure, structure_items)
        conf = structure.get('configuration')
        if conf is not None:
            check_and_suggest(conf, configuration_items)
    s.create_structures(structures, nudging)
    fname = dict_struct.get('outputfile')
    if fname is not None:
        fname = os.path.expanduser(fname)
        logger.info("Creating %s..." % fname)
        s.write_structures(fname)


def create_fluxflag(s, inputs, logger):
    """ Create fluxflag.gr3
    """
    dict_flow = inputs.get('flow_outputs')
    if dict_flow is None:
        return
    logger.info("Processing fluxflag outputs...")
    expected_items = ('linestrings', 'outputfile')
    check_and_suggest(dict_flow, expected_items)
    flowlines = dict_flow.get('linestrings')
    if flowlines is None:
        raise ValueError("No flowlines in flow_outputs")
    fname = dict_flow.get('outputfile')
    if fname is None:
        logger.info("outputfile not given for flow_outputs. Using fluxflag.prop")
        fname = 'fluxflag.prop'
    fname = os.path.expanduser(fname)
    logger.info("Creating %s..." % fname)
    s.create_flux_regions(flowlines, fname)
    with open(fname, 'a') as f:
        for line in flowlines:
            buf = '{}\n'.format(line['name'])
            f.write(buf)


def update_spatial_inputs(s, inputs, logger):
    """ Create SCHISM grid inputs.

        Parameters
        ----------
        s: SchismSetup
            schism setup object
        inputs: dict
            inputs from an input file
    """
    create_hgrid(s, inputs, logger)
    create_gr3_with_polygons(s, inputs, logger)
    create_source_sink(s, inputs, logger)
    create_prop_with_polygons(s, inputs, logger)
    create_structures(s, inputs, logger)
    create_fluxflag(s, inputs, logger)


def update_temporal_inputs(s, inputs):
    """ Create temporal inputs. Under development
    """
    # create in interpolated tide file
    sf_tide_out_fpath = os.path.join(output_dir, sf_tide_out_fname)
    s.interpolate_tide(time_start, time_end, dt,
                       sf_tide_in_fpath, sf_tide_out_fpath)
    # Run the FORTRAN code to create elev2D.th
    hgrid_out_fpath = os.path.join(output_dir, hgrid_out_fname)
    webtide_grid_fpath = os.path.join(input_dir, webtide_grid_fname)
    webtide_fpath = os.path.join(input_dir, webtide_fname)
    elev2d_fpath = os.path.join(output_dir, elev2d_fname)
    p = subprocess.Popen(["./gen_elev2D_4_NAVD88", sf_tide_out_fpath,
                          hgrid_out_fpath, webtide_grid_fpath, webtide_fpath,
                          elev2d_fpath],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    return_code = p.wait()
    if return_code != 0:
        for l in p.stdout:
            print(l)
        for l in p.stderr:
            print(l)


def item_exist(inputs, name):
    return True if name in inputs else False


def setup_logger():
    """ Set up a logger
    """
    logging_level = logging.INFO
    logging_fname = 'prepare_schism.log'
    logging.basicConfig(level=logging_level, filename=logging_fname,
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging_level)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def main():
    """ main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    prepare_schism(args)


def prepare_schism(args, use_logging=True):
    if use_logging is True:
        setup_logger()
        logger = logging.getLogger('SCHISM')
    else:
        logger = logging.getLogger('')
    logger.info("Start pre-processing SCHISM inputs...")
    in_fname = args.main_inputfile

    if not os.path.exists(in_fname):
        logger.error("The main input file, %s, is not found", in_fname)
        raise ValueError("Main input file not found")
    with open(in_fname, 'r') as f:
        inputs = schism_yaml.load(f)
    keys_top_level = ["mesh", "gr3",
                      "prop", "hydraulics",
                      "sources_sinks", "flow_outputs"] \
        + schism_yaml.include_keywords
    logger.info("Processing the top level...")
    check_and_suggest(list(inputs.keys()), keys_top_level, logger)

    out_fname = os.path.splitext(in_fname)[0] \
        + '_echo' + os.path.splitext(in_fname)[1]
    with open(out_fname, 'w') as f:
        f.write(schism_yaml.safe_dump(inputs))

    # Mesh section
    if item_exist(inputs, 'mesh'):
        logger.info("Processing mesh section...")
        mesh_items = inputs['mesh']
        keys_mesh_section = ["mesh_inputfile", "dem_list",
                             "open_boundaries",
                             "depth_optimization",
                             "gr3_outputfile", "ll_outputfile"] \
            + schism_yaml.include_keywords
        check_and_suggest(list(mesh_items.keys()), keys_mesh_section)
        if item_exist(inputs['mesh'], 'mesh_inputfile'):
            # Read the grid file to be processed
            mesh_input_fpath = \
                os.path.expanduser(mesh_items['mesh_inputfile'])
            s = create_schism_setup(mesh_input_fpath, logger)
            update_spatial_inputs(s, inputs, logger)
        else:
            raise ValueError("No mesh input file in the mesh section.")
    else:
        raise ValueError("No mesh section in the main input.")
    logger.info("Done.")


if __name__ == "__main__":
    main()
