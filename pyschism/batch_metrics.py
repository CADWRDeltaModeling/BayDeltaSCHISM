#!/usr/bin/env python
# -*- coding: utf-8 -*-

# todo
# unit conversions
""" Create metrics plots in a batch mode
    Python version 2.7
"""
import matplotlib
import pandas as pd

matplotlib.use('Agg')  # To prevent an unwanted failure on Linux
from metricsplot import (plot_metrics, plot_comparison, get_common_window,
                         safe_window, check_if_all_tss_are_bad, fill_gaps)

import matplotlib.pyplot as plt
from unit_conversions import (
    cfs_to_cms, ft_to_m, ec_psu_25c, fahrenheit_to_celcius)
import schism_yaml
from vtools.data.vtime import days, hours
from vtools.functions.error_detect import med_outliers
import argparse
from vtools.datastore.read_ts import read_ts
import station
import numpy as np
from datetime import datetime
import os
import re
import logging
from copy import deepcopy

pd.plotting.register_matplotlib_converters()

def process_time_str(val):
    return datetime(*list(map(int, re.split(r'[^\d]', val))))


def read_optional_flag_param(params, name):
    param = params.get(name)
    if param is None:
        return False
    else:
        param = param.lower()
        if param in ('true', 'yes', 'y'):
            return True
        elif param in ('false', 'no', 'n'):
            return False
        else:
            raise ValueError('Value for %s is not understood' % name)


class BatchMetrics(object):
    """ A class to plot metrics in a batch mode
    """
    VAR_2D = ('elev', )
    VAR_3D = ('salt', 'temp')
    MAP_VAR_FOR_STATIONDB = {'flow': 'flow', 'elev': 'stage', 'salt': 'wq',
                             'temp': 'wq'}
    variable_units = {'flow': 'cms', 'elev': 'm', 'salt': 'PSU',
                             'temp': 'deg C'}

    def __init__(self, params=None):
        """ Constructor
            params: dict
                parameters
        """
        self.params = params
        # self.sim_outputs = None
        # self.tss = []
        self.logger = logging.getLogger("metrics")

    def read_simulation_outputs(self, variable, outputs_dir,
                                time_basis, stations_input=None):
        """ Read simulation outputs

            Returns
            -------
            array of station_extractor.StationReader or station_extractor.FlowReader
        """
        sim_outputs = []
        if variable == 'flow':
            for i, working_dir in enumerate(outputs_dir):
                if stations_input is None:
                    station_in = os.path.join(working_dir, "flowlines.yaml")
                else:
                    station_in = stations_input[i]
                datafname = os.path.join(working_dir,"flux.out")                
                sim_out = station.read_flux_out(datafname,station_in,reftime=time_basis)
                sim_outputs.append(sim_out)
        else:
            for i, working_dir in enumerate(outputs_dir):
                if stations_input is None:
                    station_infile = os.path.join(working_dir, "station.in")
                else:
                    station_infile = stations_input[i]
                datafname = os.path.join(working_dir,station.staout_name(variable))
                sim_out = station.read_staout(datafname,station_infile,
                                              reftime=time_basis,ret_station_in = False,
                                              multi=True)
                sim_outputs.append(sim_out)
        return sim_outputs

    def retrieve_tss_sim(self, sim_outputs, station_id, variable, vert_pos=0):
        """ Collect simulation outputs

            Returns
            -------
            list of vtools.data.timeseries.TimeSeries
        """
        raise ValueError("werewte")
        tss_sim = list()
        for sim_output in sim_outputs:
            if variable == 'flow':
                ts = sim_output[station_id]
            elif variable in self.VAR_2D:
                ts = sim_output[(station_id,vert_pos)]
            elif variable in self.VAR_3D:
                ts = sim_output[(station_id,vert_pos)]
            else:
                raise ValueError('The variable is not supported yet')
            tss_sim.append(ts.to_series())
        return tss_sim

    def set_fname_out(self, alias, variable, station_id, vert_pos=0):
        """ Create a file name for graphic outputs

            Returns
            -------
            str
        """
        if alias is None:
            fout_name = "%s_%s" % (variable, station_id)
        else:
            fout_name = "%s_%s" % (variable, alias)
            if alias != station_id:
                fout_name += "_%s" % station_id
        if variable in self.VAR_3D:
            if vert_pos == 0:
                fout_name += "_upper"
            elif vert_pos == 1:
                fout_name += "_lower"
            else:
                fout_name += "_{}".format(vert_pos)
        return fout_name

#     def is_selected_station(self):
#         if self.selected_stations is None:
#             return True
#         else:
#             if self.current_station_id in self.selected_stations:
#                 return True
#             return False

    def find_obs_file(self, station_id,subloc,variable,
                      db_stations, db_obs):
        """ Find a file path of a given station_id from a link table
            of station_id and observation file names

            Returns
            -------
            str
                a file path of an observation file
        """
        mapvar = self.MAP_VAR_FOR_STATIONDB[variable]
        if station_id in db_stations:
            flag_station = db_stations.loc[station_id,mapvar]
            data_expected = not (flag_station == '')
        else:
            data_expected = False

        fpath_obs_fnd = (station_id,subloc,variable) in db_obs.index
        if fpath_obs_fnd:
            fpath_obs = db_obs.loc[(station_id,subloc,variable),"path"]
        else: 
            fpath_obs = None

        if fpath_obs_fnd:
            absfpath = os.path.abspath(fpath_obs)
            if data_expected is True:
                self.logger.info("Observation file for id {}: {}".format(station_id, absfpath))
            else:
                self.logger.warning("File link {} found for station {} but station not expected to have data for variable: {}".format(absfpath,station_id,variable))
        else:
            expectstr = '(Data not expected)' if (not data_expected)  else '(Not in the file links)'
            level = logging.WARNING if data_expected is True else logging.INFO
            self.logger.log(level, "{} No {} data link listing for: {}".format(expectstr, variable, station_id))
        return fpath_obs

    def retrieve_ts_obs(self, station_id,subloc,variable, window,
                        db_stations, db_obs):
        """ Retrieve a file name of a field data
        """
        fpath_obs = self.find_obs_file(station_id,subloc,variable,
                                       db_stations, db_obs)

        if fpath_obs:
            if os.path.exists(fpath_obs):
                try:
                    ts_obs = read_ts(fpath_obs, start=window[0], end=window[1])

                    if ts_obs.shape[1] > 1:
                        raise Exception("Multiple column series received. Need to implement selector")
                    ts_obs = ts_obs.iloc[:,0]
                except ValueError as e:
                    raise
                    self.logger.warning(
                        "Got ValueError while reading an observation file: {}".format(e))
                    ts_obs = None
                if ts_obs is None:
                    self.logger.warning(
                        "File {} does not contain useful data for the requested time window".format( os.path.abspath(fpath_obs)))
                return ts_obs
            else:
                self.logger.warning(
                    "Observation file not found on file system: {}".format(os.path.abspath(fpath_obs)))
                return None
        else:
            return None

    def convert_unit_of_ts_obs_to_SI(self, ts, unit):
        """ Convert the unit of the observation data if necessary
            WARNING: This routine alters the input ts (Side effect.)

            Returns
            -------
            vtools.data.timeseries.TimeSeries
        """
        if ts is None:
            raise ValueError("Cannot convert None")
        if unit == 'ft':
            self.logger.info("Converting the unit of obs ts from ft to m.")
            ts = ft_to_m(ts)
            ts.unit = 'm'
        elif unit == 'meter':
            ts.unit = 'm'
        elif unit == 'cfs':
            self.logger.info("Converting the unit of obs ts from cfs to cms.")
            ts = cfs_to_cms(ts)
            ts.unit = 'cms'
        elif unit == 'ec':
            self.logger.info("Converting ec to psu...")
            ts .iloc[:]= ec_psu_25c(ts)
            ts.unit = 'PSU'
        elif unit == 'psu':
            ts.unit = 'PSU'
        elif unit in ('deg F', 'degF'):
            self.logger.info("Converting deg F to deg C")
            ts = fahrenheit_to_celcius(ts)
            ts.unit = 'deg C'
        elif unit in ('degC','deg C'):
            ts.unit = 'deg C'
        elif unit is None:
            ts.unit = None
            self.logger.warning("No unit in the time series")
        elif unit == '':
            self.logger.warning("Empty (blank) unit in the time series")
        else:
            self.logger.warning(
                "  Not supported unit in the time series: {}.".format(unit))
            raise ValueError("Not supported unit in the time series: {}".format(unit))
        return ts

    def create_title(self, db_stations, station_id, source, variable, subloc):
        """ Create a title for the figure
        """
        long_name = db_stations.loc[station_id,'name']
        #todo: These should be part of station_in
        if long_name is None:
            long_name = station_id
        title = long_name

        if variable in ('salt', 'temp'):
            if subloc != 'default': title += " ({})".format(subloc)
        title += '\n'
        title += 'Source: {}, ID: {}\n'.format(source,
                                             station_id)
        return title

    def adjust_obs_datum(self, ts_obs, ts_sim, station_id, variable, subloc, db_obs):
        """ Adjust the observation automatically if the datum in obs link is
            '' or STND.
            Side Effect WARNING: This routine alters ts_obs!
        """
        # NOTE: No vert_pos...
        #todo: pandas
        datum = db_obs.loc[(station_id,variable,subloc),'vdatum']
        if datum == '' or datum == 'STND':
            self.logger.info("Adjusting obs ts automatically...")
            window = get_common_window((ts_obs, ts_sim))
            ts_obs_common = safe_window(ts_obs, window)
            ts_sim_common = safe_window(ts_sim, window)
            if ts_obs_common is None or ts_sim_common is None:
                return ts_obs, 0.
            if (np.all(np.isnan(ts_obs_common.data)) or
                    np.all(np.isnan(ts_sim_common.data))):
                return ts_obs, 0.
            adj = np.average(ts_sim.data) - np.nanmean(ts_obs.data)
            ts_obs += adj
            return ts_obs, adj
        else:
            return ts_obs, 0.

    def plot(self):
        """ Generate metrics plots
        """
        # Process input parameters
        params = self.params
        variable = params['variable']
        outputs_dir = params['outputs_dir']
        if isinstance(outputs_dir, str):
            outputs_dir = outputs_dir.split()
        time_basis = process_time_str(params['time_basis'])
        stations_input = params.get('stations_input')
        if stations_input is None:
            stations_input = params.get('flow_station_input') if variable == "flow" else params.get('station_input')
        else: 
            raise ValueError("Old style input file. \nUse 'station_input' and 'flow_station_input' respectively for staout* and flow.dat")
        if isinstance(stations_input, str):
            stations_input = stations_input.split()
        
        db_stations = station.read_station_dbase(params['stations_csv'])
        db_obs = station.read_obs_links(params['obs_links_csv'])
        excluded_stations = params.get('excluded_stations')
        selected_stations = params.get('selected_stations')
        start_avg = process_time_str(params["start_avg"])
        end_avg = process_time_str(params["end_avg"])
        start_inst = process_time_str(params["start_inst"])
        end_inst = process_time_str(params["end_inst"])
        labels = params['labels']
        dest_dir = params.get('dest_dir')
        if dest_dir is None:
            dest_dir = '.'
        else:
            if not os.path.exists(dest_dir):
                os.mkdir(dest_dir)
        plot_format = params.get('plot_format')
        padding = days(4)
        window_common = (min(start_inst, start_avg),
                         max(end_inst, end_avg))
        window_to_read = (window_common[0] - padding,
                          window_common[1] + padding)
        plot_all = read_optional_flag_param(params, 'plot_all')
        remove_outliers = read_optional_flag_param(params, 'remove_outliers')
        adjust_datum = read_optional_flag_param(params, 'auto_adjustment')
        fill_gap = read_optional_flag_param(params, 'fill_gap')
        max_gap_to_fill = hours(1)
        if 'max_gap_to_fill' in params:
            max_gap_to_fill =pd.tseries.frequencies.to_offset(params['max_gap_to_fill'])
        else: max_gap_to_fill = hours(1)
        

        # Prepare readers of simulation outputs
        sim_outputs = self.read_simulation_outputs(variable,
                                                   outputs_dir,
                                                   time_basis,
                                                   stations_input)
        assert len(sim_outputs) > 0
        assert sim_outputs[0] is not None

        # Iterate through the stations in the first simulation outputs
        for stn in sim_outputs[0].columns:
            station_id = stn[0] if type(stn) == tuple else stn
            # Prepare
            self.logger.info(
                "==================================================")

            self.logger.info("Start processing station:: {}".format(station_id))

            if not station_id in db_stations.index:
                self.logger.warning("Station id {} not found in station listings".format(station_id))
                continue
            alias = db_stations.loc[station_id,'alias']

            if selected_stations is not None:
                if station_id not in selected_stations:
                    self.logger.info("Skipping..."
                                     " Not in the list of the selected stations: %s",
                                     station_id)
                    continue
            if excluded_stations is not None:
                if station_id in excluded_stations:
                    self.logger.info("Skipping... "
                                     "In the list of the excluded stations: %s",
                                     station_id)
                    continue
                
            if variable == 'flow':
                vert_pos = 'default'
            else:
                vert_pos = stn[1]
            adj_obs = 0.

            # Read Obs
            subloc = 'default' if variable == 'flow' else stn[1]
            ts_obs = self.retrieve_ts_obs(station_id,subloc, variable, window_to_read,
                                          db_stations, db_obs)


            if ts_obs is None or ts_obs.isnull().all():
                self.logger.warning("No observation data: %s.",
                                    station_id)
                if plot_all is False:
                    self.logger.warning("Skipping this station")
                    continue
            else:
                if remove_outliers is True:
                    self.logger.info("Removing outliers...")
                    ts_obs = med_outliers(ts_obs, level=3, copy=False)
                adj = db_obs.loc[(station_id,subloc,variable),'datum_adj']
                if adj is not None and adj != 0.:
                    self.logger.info(
                        "Adjusting obs value with the value in the table...")
                    ts_obs += adj
                    
                    if obs_unit == 'ft':
                        adj = ft_to_m(adj)
                    else:
                        ValueError("Not supported unit for adjustment.")
                    adj_obs += adj
                try:
                    obs_unit = db_obs.loc[(station_id, subloc, variable),'unit']

                    ts_obs = self.convert_unit_of_ts_obs_to_SI(ts_obs,obs_unit)
                    
                    obs_unit = ts_obs.unit
                except Exception as e:
                    raise Exception("Station {}".format(station_id)) from e

            # Read simulation
            if variable == "flow":
                tss_sim = [None if simout[station_id].isnull().all() else simout[station_id] for simout in sim_outputs]

            else:
                tss_sim = [simout.loc[:,(station_id,subloc)].iloc[:,0] for simout in sim_outputs]
            
            for ts in tss_sim:
                if ts is None: continue
                if ts_obs is None or ts_obs.isnull().all(): 
                    ts.unit = self.variable_units[variable] 
                else:
                    ts.unit = obs_unit

            # Adjust datum if necessary
            if adjust_datum and ts_obs is not None:
                ts_obs, adj = self.adjust_obs_datum(ts_obs,                        
                                                    tss_sim[0],
                                                    station_id,
                                                    variable,
                                                    db_obs)
                adj_obs += adj
            if ts_obs is not None and fill_gap is True:
                self.logger.info("Filling gaps in the data.")
                fill_gaps(ts_obs, max_gap_to_fill)

            # Plot
            if check_if_all_tss_are_bad([ts_obs] + tss_sim):
                self.logger.error("None of time series have data.")
                continue
            self.logger.info("Start plotting...")
            source = db_obs.loc[(station_id,subloc,variable),"agency"].upper()
            figtitle = self.create_title(
                db_stations, station_id, source, variable, vert_pos)
            
            title = None
            if type(tss_sim) == list: tss_sim=tuple(tss_sim)

            # labels
            labels_to_plot = deepcopy(labels)
            if adj_obs != 0.:
                if adj_obs > 0.:
                    labels_to_plot[0] += " + {:g}".format(adj_obs)
                else:
                    labels_to_plot[0] += " - {:g}".format(-adj_obs)
            
            if plot_format == 'simple':
                fig = plot_comparison(ts_obs, tss_sim,
                                      window_inst=(start_inst, end_inst),
                                      window_avg=(start_avg, end_avg),
                                      labels=labels_to_plot,
                                      title=title)
            else:
                fig = plot_metrics(ts_obs, tss_sim,
                                   window_inst=(start_inst, end_inst),
                                   window_avg=(start_avg, end_avg),
                                   labels=labels_to_plot,
                                   title=title)
            fname_output = self.set_fname_out(alias,
                                              variable,
                                              station_id,
                                              vert_pos)
            fpath_output = os.path.join(dest_dir, fname_output + '.png')
            fig.suptitle(figtitle,fontsize=14)
            fig.savefig(fpath_output, dpi=300)
            self.logger.info("Done for the station.")


def create_arg_parser():
    """ Create an argument parser
        return: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser()
    # Read in the input file
    parser = argparse.ArgumentParser(
        description="Create metrics plots in a batch mode")
    parser.add_argument(dest='main_inputfile', default=None,
                        help='main input file name')
    return parser


def init_logger():
    """ Initialize a logger for this routine
    """
    logging.basicConfig(level=logging.INFO,
                        filename="metrics.log",
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    #%(asctime)s - %(name)s - %(levelname)s
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    filer = logging.FileHandler('metrics_missing.log', mode='w')
    filer.setLevel(logging.WARNING)
    formatter2 = logging.Formatter('%(name)s - %(message)s')
    filer.setFormatter(formatter2)
    logging.getLogger('').addHandler(filer)
    logging.getLogger('').addHandler(console)


def get_params(fname):
    """ Read in parameters from a YAML file
    """
    with open(fname, 'r') as fin:
        params = schism_yaml.load_raw(fin)
    return params


def main():
    """ Main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    params = get_params(args.main_inputfile)
    init_logger()
    BatchMetrics(params).plot()

if __name__ == "__main__":
    main()
