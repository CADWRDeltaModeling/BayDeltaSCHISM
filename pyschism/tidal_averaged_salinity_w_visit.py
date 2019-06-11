#!/usr/bin/env python2
# -*- coding: utf-8 -*-
""" Routines to make time average of salinity over a whole domain
    using VisIt.
    VisIt Python package that comes with VisIt installation should be in
    the PYTHONPATH. For example, it is under current/linux-x86_64/lib/site-packages
    in case of Linux VisIt.

    The routines requires Python 2.7, following the VisIt plug-in version.
"""
from __future__ import print_function
import os
import visit

__author__ = "Kijin Nam <knam@water.ca.gov>"
__license__ = "GPLv3"

__all__ = ['average_salinity_over_time_w_visit',
           'convert_psu_to_ec_w_visit',
           'subtract_one_from_other_w_visit'
           'calculate_difference_of_tidal_average_salinity']


def average_salinity_over_time_w_visit(visit_inputfile,
                                       outputfile_prefix,
                                       var_name_to_average='salt_depth_average',
                                       var_name_to_write='salt_tidal_depth_average'):
    """ Calculate time-average of depth-averaged salinity using VisIt and plug-ins.
        All time steps available in the input file(s) are used for averaging.
        The output file format is Silo.

        Parameters
        ----------
        visit_inputfile: path-like
            a visit file that contains a list of SCHISM binary output files.
        outputfile_prefix: str
            a output file prefix. Nothing is attached to the prefix for now.
        var_name_to_substract: str, optional
            a variable name to subtract one from the other.
            The default value is 'salt_depth_average.'
        var_name_to_write: str, optional
            a variable name to use in the output file
            The default value is 'salt_tidal_depth_average.'
    """
    fpath_out = outputfile_prefix + '.silo'
    if os.path.exists(fpath_out):
        os.remove(fpath_out)
    visit.AddArgument('-nowin')
    visit.Launch()
    visit.OpenComputeEngine('localhost', ('-l', 'serial'))

    visit.OpenDatabase(visit_inputfile, 0, "SCHISM_2.0")

    visit_expression = "average_over_time({})".format(
        var_name_to_average)
    visit.DefineScalarExpression(var_name_to_write, visit_expression)
    visit.AddPlot("Pseudocolor", var_name_to_write, 1, 1)
    visit.DrawPlots()

    ExportDBAtts = visit.ExportDBAttributes()
    ExportDBAtts.allTimes = 0
    ExportDBAtts.db_type = "Silo"
    ExportDBAtts.filename = outputfile_prefix
    ExportDBAtts.dirname = "."
    ExportDBAtts.variables = (var_name_to_write)
    ExportDBAtts.opts.types = (0)
    visit.ExportDatabase(ExportDBAtts)
    visit.DeleteActivePlots()
    visit.Close()


def subtract_one_from_other_w_visit(file_base, file_alternative,
                                    outputfile_prefix,
                                    var_name_to_subtract='salt_tidal_depth_average',
                                    var_name_to_write='diff_salt_tidal_depth_average'):
    """ Calculate the difference by subtracting values in one Silo file
        from another.
        The output file format is Silo.

        Parameters
        ----------
        file_base: str
            a pathname to a Silo file for the base case. Values in this file will be subtracted.
        file_alternative: str
            a pathname to a Silo file for the alternative case, which will be subtracted from.
        outputfile_prefix: str
            a output file prefix. Nothing is attached to the prefix for now.
        var_name_to_substract: str, optional
            a variable name to subtract one from the other.
            The default value is 'salt_tidal_depth_average'
        var_name_to_write: str, optional
            a variable name to use in the output file
            The default value is 'diff_salt_tidal_depth_average'
    """
    fpath_out = outputfile_prefix + '.silo'
    if os.path.exists(fpath_out):
        os.remove(fpath_out)

    visit.AddArgument('-nowin')
    visit.Launch()
    visit.OpenComputeEngine('localhost', ('-l', 'serial'))

    visit.OpenDatabase(file_alternative, 0)
    visit.OpenDatabase(file_base, 0)

    eqn = "(conn_cmfe(<{}:{}>, <2D_Mesh>) - {})".format(file_alternative,
                                                        var_name_to_subtract, var_name_to_subtract)
    visit.DefineScalarExpression(var_name_to_write, eqn)
    visit.AddPlot("Pseudocolor", var_name_to_write, 1, 0)
    visit.DrawPlots()

    # Export diff
    ExportDBAtts = visit.ExportDBAttributes()
    ExportDBAtts.allTimes = 0
    ExportDBAtts.db_type = "Silo"
    ExportDBAtts.filename = outputfile_prefix
    ExportDBAtts.dirname = "."
    ExportDBAtts.variables = (var_name_to_write)
    ExportDBAtts.opts.types = (0)
    visit.ExportDatabase(ExportDBAtts)

    visit.Close()


def convert_psu_to_ec_w_visit(visit_inputfile,
                              outputfile_prefix=None,
                              var_name_to_convert='salt_depth_average',
                              var_name_to_write='salt_depth_average_ec'):
    """ Convert salinity in PSU into EC unit.
        The input file format is assumed in Silo, which VisIt can understand
        without plug-ins.

        Parameters
        ----------
        visit_inputfile: str, path-like
            a visit file that contains a list of SCHISM binary output files.
        outputfile_prefix: str, optional
            a output file prefix.
            If it is not given, '_ec' will be added to the input file name.
        var_name_to_substract: str, optional
            a variable name to subtract one from the other.
            The default value is 'salt_depth_average'
        var_name_to_write: str, optional
            a variable name to use in the output file
    """
    if outputfile_prefix is None:
        outputfile_prefix = os.path.splitext(visit_inputfile)[0]
    outputfile_prefix += '_ec'
    fpath_out = outputfile_prefix + '.silo'
    if os.path.exists(fpath_out):
        os.remove(fpath_out)

    visit.AddArgument('-nowin')
    visit.Launch()
    visit.OpenComputeEngine('localhost', ('-l', 'serial'))

    eqn = "{} / 35 * 53087 + {} * ({} - 35) * (-16.072 + 4.1495 * {} ^ 0.5 - 0.5345 * {} + 0.0261 *   {} ^ 0.75)".format(
        *[var_name_to_convert for _ in range(6)])

    visit.OpenDatabase(visit_inputfile, 0)
    visit.DefineScalarExpression(var_name_to_write, eqn)
    visit.AddPlot("Pseudocolor", var_name_to_write, 1, 0)
    visit.DrawPlots()

    # Export diff
    ExportDBAtts = visit.ExportDBAttributes()
    ExportDBAtts.allTimes = 0
    ExportDBAtts.db_type = "Silo"
    ExportDBAtts.filename = outputfile_prefix
    ExportDBAtts.dirname = "."
    ExportDBAtts.variables = (var_name_to_write)
    ExportDBAtts.opts.types = (0)
    visit.ExportDatabase(ExportDBAtts)

    visit.Close()


def calculate_difference_of_tidal_average_salinity(file_base, file_alternative,
                                                   outputfile_prefix,
                                                   convert_to_ec=False):
    """ Calculate salinity difference from two cases.
        This function simply runs the functions above in a row
        for convenience.
        Note that intermediate files will be overwritten.

        Parameters
        ----------
        file_base: str
            A base case file
        file_alternative: str
            A alternative case file.
        outputfile_prefix: str
            a output file prefix. Nothing is attached to the prefix for now.
        convert_to_ec: boolean, optional
            a switch to convert PSU into EC. The default value is False.
    """
    intermediate1_prefix = 'salt_tidal_avg_base'
    intermediate2_prefix = 'salt_tidal_avg_alt'
    average_salinity_over_time_w_visit(file_base,
                                       intermediate1_prefix)
    average_salinity_over_time_w_visit(file_alternative,
                                       intermediate2_prefix)
    if convert_to_ec:
        convert_psu_to_ec_w_visit(intermediate1_prefix + '.silo')
        convert_psu_to_ec_w_visit(intermediate2_prefix + '.silo')
        subtract_one_from_other_w_visit(
            intermediate1_prefix + '_ec.silo', intermediate2_prefix + '_ec.silo', outputfile_prefix, var_name_to_subtract='salt_depth_average_ec')
    else:
        subtract_one_from_other_w_visit(intermediate1_prefix + '.silo',
                                        intermediate2_prefix + '.silo',
                                        outputfile_prefix)
