"""Predict SMSCG tidal open and close hours by linear regression.

   The prediction is based on linear regression models that relate tidal open and close hours to SRV flow, MRZ Tidal energy, 
   and CSE-MRZ elevation difference. User need to provide astonoic tidal ddata as inputs, if not given, the prediction 
   is based on modeling data repo and may be less accurate.

"""

import logging
import os
import re
import numpy as np
import pandas as pd
from pathlib import Path
import click
from dms_datastore.read_multi import read_ts_repo
from vtools.functions.filter import cosine_lanczos
from vtools.functions.tidalhours import hour_tide
import datetime as dtm
import matplotlib.pyplot as plt
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource,Range1d,LinearAxis
from bokeh.io import output_notebook,show,output_file,export_png
from bokeh.layouts import row,grid,column

logger = logging.getLogger(__name__)

def predict_gate_op(flow,diff_cse_mrz_elev,mrz_energy,tideh_flow,tideh_mrz,gate_op_period):
    """ Predict gate operation based on index flow, MRZ elevation, and CSE-MRZ elevation difference.
    
    Parameters:     

    flow (pd.Series): Index flow data, now use SRV ONLY flow
    diff_cse_mrz_elev (pd.Series): CSE-MRZ elevation difference data.
    mrz_energy (pd.Series): MRZ energy data.
    tideh_ndo (pd.Series): Tidal hours at NDO.
    tideh_mrz (pd.Series): Tidal hours at MRZ.
    gate_op_period (list): list of Gate tidal operation start and end times, such as [[start_date1, end_date1], 
    [start_date2, end_date2]]

    all the input time sereies should have the same length and aligned time index
    """  
    predicted_mrz_tidalop_open_t = 5.8217+0.1076*flow/5000-0.1464*mrz_energy-1.5802*diff_cse_mrz_elev
    #predicted_ndo_tidalop_close_t = 6.1197-0.0209*ndo/5000
    ## here is srv flow to do prediction
    predicted_flow_tidalop_close_t = 6.3976-0.0742*flow/5000-0.0426*mrz_energy+0.2421*diff_cse_mrz_elev
    
    dtindex = flow.index
    ## keep the tideh_flow,tideh_mrz times that are in the range of 2 to 8
    invalid_tideh_flow = (tideh_flow > 8) | (tideh_flow < 2)
    invalid_tideh_mrz = (tideh_mrz > 8) | (tideh_mrz < 2)
    invalid_open_id = np.where(invalid_tideh_mrz)[0]
    invalid_close_id = np.where(invalid_tideh_flow)[0]
    invalid_open_time = dtindex[invalid_open_id]
    invalid_close_time = dtindex[invalid_close_id]

    
    ## second round of filtering find out those tide hours whose difference between two
    ## neibors are larger than 0.5 h, those are outliers caused by inaccurate tidal elevation data
    mrz_diff = abs(np.diff(tideh_mrz))
    mask = (mrz_diff[1:] > 0.5) & (mrz_diff[:-1] > 0.5)
    invalid_open_id2 = np.where(mask)[0] + 1  # +1 to adjust for the diff operation
    ## inculde id before and after the invalid open id
    invalid_open_id2 = np.concatenate([invalid_open_id2-1,invalid_open_id2+1,invalid_open_id2])
    invalid_open_id2 = np.clip(invalid_open_id2, 0, len(dtindex)-1)  # Ensure indices are within bounds
    invalid_open_id2 = np.unique(invalid_open_id2)  # Remove duplicates

    
    invalid_open_time= pd.DatetimeIndex(np.concatenate([invalid_open_time, dtindex[invalid_open_id2]])).sort_values()
    

    tideh_flow_diff = abs(np.diff(tideh_flow))
    mask = (tideh_flow_diff[1:] > 0.5) & (tideh_flow_diff[:-1] > 0.5)
    invalid_close_id2 = np.where(mask)[0] + 1  # +1 to adjust for the diff operation
    invalid_close_id2 = np.concatenate([invalid_close_id2-1,invalid_close_id2+1,invalid_close_id2])
    invalid_close_id2 = np.clip(invalid_close_id2, 0, len(dtindex)-1)  # Ensure indices are within bounds
    invalid_close_id2 = np.unique(invalid_close_id2)  # Remove duplicates
    invalid_close_time= pd.DatetimeIndex(np.concatenate([invalid_close_time, dtindex[invalid_close_id2]])).sort_values()

    ## when predicted gate open/close tidal hour equals the tidal hour for a time stamp, 
    # it indicates a potential gate operation time.
    ## here intersect flow tidehour  and predicted flow tidal close hour to find the gate close candidates
    diff1 = tideh_flow-predicted_flow_tidalop_close_t
    ss=np.sign(diff1).diff().fillna(0).astype(bool)
    gate_close_candidates = diff1.index[ss]
    gate_close_candidates = [s for s in gate_close_candidates if s not in invalid_close_time]
    ## here intersect tidehour mrz and predicted mrz tidal open hour to find the gate close candidates
    diff2 = tideh_mrz - predicted_mrz_tidalop_open_t
    ss=np.sign(diff2).diff().fillna(0).astype(bool)
    gate_open_candidates = diff2.index[ss]
    gate_open_candidates = [s for s in gate_open_candidates if s not in invalid_open_time]

    #gate_op_no_duplicate = gate_op[gate_op['op'].shift() != gate_op['op']]
    
    ## there are some open times pairs where neibors are close within 3 hours
    ## find out them, use first of them as the valid open time, and remove the one
    ## just after the pair
   
    tdiff = np.abs(np.diff(gate_open_candidates))
    mask = tdiff < pd.Timedelta(hours=3)
    re_open_id = np.where(mask)[0] 
   
    bogus_open_id = re_open_id[1::2]
    bogus_open_id2 = bogus_open_id + 1
    bogus_open_id = np.concatenate([bogus_open_id,bogus_open_id2])
    gate_open_candidates = [element for index, element in enumerate(gate_open_candidates) if index not in bogus_open_id]
    
    #op_start = np.where(gate_op_no_duplicate['op']==-10)[0]
   # op_end = np.where(gate_op_no_duplicate['op']!=-10)[0]
    # in case no ending timestamp for the last gate opening timestamp
    # drop last gate opening data
    #op_start_in_end = np.searchsorted(op_end, op_start)
    #if (op_start_in_end[-1]>(len(op_end)-1)): 
    #    op_start=op_start[:-1]
    
    
    #op_lst = [[gate_op_no_duplicate.index[i],gate_op_no_duplicate.index[op_end[op_start_in_end[j]]]] for i,j in zip(op_start,range(len(op_start)))]
    op_lst  = gate_op_period
    gate_open_close_lst = []
    
    for op in op_lst:
        open_id = np.searchsorted(gate_open_candidates, op)
        valid_gate_open_candidates = gate_open_candidates[open_id[0]:open_id[1]]
        close_id = np.searchsorted(gate_close_candidates, op)
        valid_gate_close_candidates = gate_close_candidates[close_id[0]:close_id[1]]
        
        # interwave valid_gate_open_candidates and valid_gate_close_candidates
        if len(valid_gate_open_candidates) > 0 and len(valid_gate_close_candidates) > 0:
            ## pair the valid gate /open/close candidate
            close_start_loc = np.searchsorted(valid_gate_close_candidates,valid_gate_open_candidates[0])
            valid_gate_close_candidates = valid_gate_close_candidates[close_start_loc:]
            paired_gate_op = [item for pair in zip(valid_gate_open_candidates, valid_gate_close_candidates) for item in pair] 
            if (len(paired_gate_op) % 2) != 0:
                # if the length of paired_gate_op is odd, remove the last element
                paired_gate_op = paired_gate_op[:-1]    
            gate_open_close_lst.append(paired_gate_op)

    ## here are some debug plots
    # x_range = (dtindex[0], dtindex[-1])
    # p1 = figure(title="Open (MRZ Astro) and Close (NDO Astro) Tidal Hours ", x_axis_type="datetime",\
    #              width=1600, height=700,x_range=x_range)
    # p1.circle(dtindex, tideh_flow, size=5,color="blue", legend_label="Tidal Hours (SRV)",)
    # p1.circle(dtindex,tideh_mrz,size=5, color="green", legend_label="Tidal Hours (MRZ)",)
    # p1.line(dtindex,predicted_mrz_tidalop_open_t,line_width=2, color="green", \
    #         legend_label="Predicted Tidal Open Hours (MRZ)")
    # p1.line(dtindex,predicted_flow_tidalop_close_t,line_width=2, color="blue", \
    #         legend_label="Predicted Tidal Close Hours (SRV)")
    # p1.y_range.start = 2
    # p1.y_range.end = 8
    
    # output_notebook()
    # output_file("tidal_ops_predict_debug.html") 
    # show(column(p1))
    return gate_open_close_lst


def load_ts(start,end):
    """Load time series data from model data repository.

       Load mrz, cse elev and srv flow from the delta repository.
       
       Parameters:
       start (datetime): Start time of the time series data to load.
       end (datetime): End time of the time series data to load.
    """
    def _as_series(ts, label):
        if isinstance(ts, pd.DataFrame):
            if ts.shape[1] != 1:
                raise ValueError(f"Expected one column for {label}, got {ts.shape[1]}")
            ts = ts.iloc[:, 0]
        elif not isinstance(ts, pd.Series):
            raise TypeError(f"Expected Series or DataFrame for {label}, got {type(ts)!r}")
        ts = ts.copy()
        ts.name = label
        return ts

    cse_elev = _as_series(
        read_ts_repo("cse", "elev", subloc="upper",start=start, end=end, force_regular=True),
        "cse_elev",
    )
    
    mrz_elev = _as_series(
        read_ts_repo("mrz", "elev", subloc="upper", start=start, end=end, force_regular=True),
        "mrz_elev",
    )
    srv_flow = _as_series(
        read_ts_repo("srv", "flow", start=start, end=end, force_regular=True),
        "srv_flow",
    )

    if not (cse_elev.index.equals(mrz_elev.index) and cse_elev.index.equals(srv_flow.index)):
        raise ValueError("cse elev, mrz elev, and srv flow must have identical timestamps")

    

    return srv_flow, mrz_elev, cse_elev


def load_ts_from_repo(start, end):
    """Backward-compatible wrapper for load_ts."""
    return load_ts(start, end)

def load_ts_harmonic(repo):
    """Load predicted time series data from tidal harmonic analysis when gate tidal operations are considered 
       from the specified repository.

       Parameters:
       repo (str): Name of the repository to load harmonic data from.

       Returns:
       cse_elev (pd.Series): Predicted astronomical elev time series data at station cse.
       mrz_elev (pd.Series): Predicted astronomical elev time series data at station mrz.
       srv_flow (pd.Series): Predicted astronomical flow time series data at station srv.
       srv_flow_d1 (pd.Series): Predicted astronomical flow time series data with diurnal component at station srv.

    """
    station = ["cse", "mrz"]
    files_to_be_used = {}
    for sta in station:
        ## match any file under repository for the current station if file name contains the station name
        files = [f for f in os.listdir(repo) if sta in f]
        if not files:
            raise FileNotFoundError(f"No files found for station {sta} in repository {repo}")
        files.sort()  # Optional: sort the files if needed
        # if multiple files match, select the most recent one based on sorting
        astro_tide_file = files[-1]  
        astro_tide_file = os.path.join(repo, astro_tide_file)
        files_to_be_used[sta] = astro_tide_file
        ## this one assumed vtide format

        

    ## read in in srv flow now
    station = "srv"
    ## for astronomical flow at srv
    srv_flow_files = [f for f in os.listdir(repo) if station in f and "all" in f ]
    srv_flow_files.sort()
    srv_flow_file = srv_flow_files[-1]  # select the most recent one
    srv_flow_file = os.path.join(repo, srv_flow_file)
    files_to_be_used["srv_flow"] = srv_flow_file
    srv_d1_flow_files = [f for f in os.listdir(repo) if station in f and "d1" in f ]  ## diuranl signal only
    srv_d1_flow_files.sort()
    srv_d1_flow_file = srv_d1_flow_files[-1]  # select the most recent one
    srv_d1_flow_file = os.path.join(repo, srv_d1_flow_file)
    files_to_be_used["srv_d1_flow"] = srv_d1_flow_file

    result_ts = {}
    print("Files to be used:", files_to_be_used)
    for key, file in files_to_be_used.items():
        #print(f"{key}: {file}")
        data = pd.read_csv(file,parse_dates=True,index_col=0,\
                        dtype=float,header=None,date_format="%m/%d/%Y %H:%M",\
                        sep=",") # 
        if not data.empty:
            t0 = data.index[0]
            t1 = data.index[-1]
            new_index = pd.date_range(start=t0, end=t1, freq='15min')
            new_data = pd.Series(data.values.squeeze(),index=new_index)
            data = new_data
        result_ts[key] = data

    ## if srv diurnal flow is not available, use the full flow series as the diurnal flow
    if "srv_d1_flow" not in result_ts or result_ts["srv_d1_flow"] is None:
        logger.info("No diurnal flow available for srv, using full flow series: %s", files_to_be_used["srv_flow"])
        result_ts["srv_d1_flow"] = result_ts["srv_flow"]

    return result_ts["cse"],result_ts["mrz"], result_ts["srv_flow"], result_ts["srv_d1_flow"]

def smscg_gate(flow_srv, elev_diff_filtered, elev_mrz, flow_srv_d1=None,gate_op_period=None):
    """Predict SMSCG gate operations based on tidal and flow data.

    Parameters:
    flow_srv (pd.Series): Service flow time series.
    elev_diff_filtered (pd.Series): Filtered elevation difference between cse and mrz.
    elev_mrz (pd.Series): MRZ elevation time series.

    Returns:
    list: List of predicted gate open/close times.
    """
    elev_mrz_filtered = cosine_lanczos(elev_mrz, '40h') 
    flow_srv_filtered = flow_srv_d1
    if flow_srv_d1 is None:
        flow_srv_filtered = cosine_lanczos(flow_srv, '16h') 
    
    energy_mrz = (elev_mrz-elev_mrz_filtered)**2
    daysindex = (flow_srv.index - flow_srv.index[0]).total_seconds() / 86400.0
    tideh_srv_flow = hour_tide(daysindex, u=flow_srv.values, leave_mean=True)
    tideh_mrz = hour_tide(daysindex, h=elev_mrz.values, leave_mean=True,start_datum="flood")
    ## covert tideh_srv_flow and tideh_mrz to pandas Series with datetime index
    tideh_srv_flow = pd.Series(tideh_srv_flow, index=flow_srv.index)
    tideh_mrz = pd.Series(tideh_mrz, index=elev_mrz.index)

    if gate_op_period is None:
        gate_op_period = [[flow_srv.index[0], flow_srv.index[-1]]]
    gate_open_close_lst = predict_gate_op(
        flow_srv_filtered,
        elev_diff_filtered,
        energy_mrz,
        tideh_srv_flow,
        tideh_mrz,
        gate_op_period,
    )
    expand_predict_index = []
    expand_predict_op = []
    for index_period in gate_open_close_lst:
        expand_predict_index.extend(index_period)
        expand_predict_op.extend([1.0, 0.0] * (int(len(index_period) / 2)))

    gate_op_ts = pd.Series(expand_predict_op, index=expand_predict_index, name="open")
    gate_op_ts = gate_op_ts.sort_index()
    return gate_op_ts


def plot_gate_op_ts(predict_smscg):
    """Plot predicted gate operation time series."""
    p1 = figure(title="SMSCG Tidal Operation", x_axis_type="datetime",\
                    width=1600, height=400)
    p1.yaxis.axis_label = "Height (ft)"
    p1.title.text_font_size = '20pt'
    p1.xaxis.axis_label_text_font_size = '15pt' 
    p1.yaxis.axis_label_text_font_size = '15pt' 
   
    op_index  = predict_smscg.index
    op_len = len(op_index)
  
        ## create a value array 10 when gate_op['op'] < 0, otherwise 0
    y = np.where(predict_smscg == 1, 24, 0) 
        # insert y values to original y  after every  element
    y2 = np.repeat(y,2)     
    y1= np.array([0,0]*(op_len))
    x = np.repeat(op_index.values[1:],2)
    # insert the first value of op_index to the beginning of x
    x = np.insert(x,0,op_index.values[0])
    # append the last value of op_index to the end of x
    x = np.append(x,op_index.values[-1])
    p1.varea(x=x,y1=y1,y2=y2,
                fill_color="lightgrey",
                fill_alpha=0.7,legend_label="Predicted Gate Open")
    p1.y_range=Range1d(start=0, end=25)
    p1.legend.label_text_font_size = '14pt'
    output_notebook()
    output_file("predicted_smscg_op.html")
    show(column(p1))


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Generate predicted SMSCG gate operation time series from tide and flow data.",
)
@click.option("--sdate", default=None, help="Start date, e.g. 2024-04-16.")
@click.option("--edate", default=None, help="End date, e.g. 2025-01-01.")
@click.option(
    "--csv-path",
    "csv_path",
    type=click.Path(path_type=Path),
    required=True,
    help="CSV path to write the output from smscg_gate.",
)
@click.option("--plot", is_flag=True, default=False, help="Plot the predicted gate operation time series.")
@click.option(
    "--astronomical-tide-path",
    "astronomical_tide_path",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Path to the astronomical tide data containing cse and mrz elevation plus srv flow.",
)
@click.option("--logdir", default=None, type=click.Path(), help="Directory for log files.")
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
def smscg_cli(sdate, edate, csv_path, plot, astronomical_tide_path, logdir, debug):
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
        logfile_prefix="smscg_gate",
    )

    if sdate is None or edate is None:
        raise ValueError("Start date and end date must be provided.")

    start = pd.Timestamp(sdate)
    end = pd.Timestamp(edate)

    if astronomical_tide_path is not None:
        logger.info("Loading harmonic tide data from %s", astronomical_tide_path)
        elev_cse, elev_mrz, flow_srv, flow_srv_d1 = load_ts_harmonic(astronomical_tide_path)
    else:
        logger.info("Loading time series data from repo between %s and %s", start, end)
        flow_srv, elev_mrz, elev_cse = load_ts(start, end)
        flow_srv_d1 = flow_srv

    elev_diff = elev_cse - elev_mrz
    elev_diff_filtered = cosine_lanczos(elev_diff, cutoff_period="12h")
    logger.info("Computing predicted gate operation series")
    gate_op_ts = smscg_gate(flow_srv, elev_diff_filtered, elev_mrz, flow_srv_d1, [[start, end]])
    logger.info("Saving predicted gate operation series to %s", csv_path)
    gate_op_ts.to_csv(csv_path, header=True)

    if plot:
        plot_gate_op_ts(gate_op_ts)


if __name__ == "__main__":
    smscg_cli()