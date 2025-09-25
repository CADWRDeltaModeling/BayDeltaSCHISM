## read in dms_smsdg_gate.csv historical log and conver to schism_th format

import pandas as pd 
import os
import pdb
import click
from pathlib import Path



@click.command(
    help=(
        "The tool convert smscg gate op log file into SCHISM raidal gate, flashboard and \
        boatlock th file \n\n"
        "Example:\n"
        "  log_2_schism_th --log dms_smscg_gate.csv --dest ./ "
    )
)

@click.option(
    "--log",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="original smscg operation log file.",
)

@click.option(
    "--dest",
    required=True,
    default="./",
    type=click.Path(exists=True, path_type=Path),
    help="folder where result SCHISM th files will be saved to",
)


def smscg_log_2_schism_th(log,dest):
    log_df = pd.read_csv(log, sep=",", header=0, parse_dates=True,
                     date_format="%Y-%m-%d %H:%M%S", index_col=0)
    tt= pd.to_datetime(log_df.index)    
    log_df.index = tt
    log_df_no_dupes = log_df[~log_df.index.duplicated(keep='first')]
    log_df_no_dupes = log_df_no_dupes.sort_index()

    ## convert to schism flashboard, radial gate and boat lock th format
    ## generate flashboard  and boatlock th format
    schism_fb_th = pd.DataFrame(index=log_df_no_dupes.index)
    schism_fb_th['install'] = [1]*len(schism_fb_th)
    schism_fb_th['ndup'] = [1]*len(schism_fb_th)  
    schism_fb_th['elev'] = [-5.34]*len(schism_fb_th)   
    schism_fb_th['width'] = [20.73]*len(schism_fb_th)

    schism_bl_th = pd.DataFrame(index=log_df_no_dupes.index)
    schism_bl_th['install'] = [1]*len(schism_fb_th)
    schism_bl_th['ndup'] = [1]*len(schism_fb_th)  
    schism_bl_th['elev'] = [-2.29]*len(schism_fb_th)   
    schism_bl_th['width'] = [6.10]*len(schism_fb_th)

    ## get all index where log_df_no_dupes['flashboards'] == "IN"
    fb_index = log_df_no_dupes.index[log_df_no_dupes['flashboards'] == "IN"]
    schism_fb_th.loc[fb_index, 'op_down'] = 0
    schism_fb_th.loc[fb_index, 'op_up'] = 0
    schism_bl_th.loc[fb_index, 'op_down'] = 1
    schism_bl_th.loc[fb_index, 'op_up'] = 1

    ## get all index where log_df_no_dupes['flashboards'] == "OUT"
    fb_index = log_df_no_dupes.index[log_df_no_dupes['flashboards'] == "OUT"]
    schism_fb_th.loc[fb_index, 'op_down'] = 1   
    schism_fb_th.loc[fb_index, 'op_up'] = 1
    schism_bl_th.loc[fb_index, 'op_down'] = 0
    schism_bl_th.loc[fb_index, 'op_up'] = 0

    ## generate radial gate th format
    schism_gate_th = pd.DataFrame(index=log_df_no_dupes.index)
    schism_gate_th['install'] = [1]*len(schism_fb_th)
    schism_gate_th['ndup'] = [3]*len(schism_fb_th)  
    schism_gate_th['elev'] = [-6.86]*len(schism_fb_th)   
    schism_gate_th['width'] = [10.97]*len(schism_fb_th)
    schism_gate_th['height'] = [10]*len(schism_fb_th)
    schism_gate_th['op_down'] = [0.0]*len(schism_fb_th)
    schism_gate_th['op_up'] = [0.0]*len(schism_fb_th)
    ## count number of open in log_df_no_dupes column "gate_1","gate_2" and "gate_3"
    ndup = 3
    for i in range(len(log_df_no_dupes)):
        open_count = 0
        if log_df_no_dupes.iloc[i]['gate_1'] == "Open":
            open_count += 1
        if log_df_no_dupes.iloc[i]['gate_2'] == "Open":
            open_count += 1
        if log_df_no_dupes.iloc[i]['gate_3'] == "Open":
            open_count += 1

        tidal_count = 0

        if log_df_no_dupes.iloc[i]['gate_1'] == "Tidal":
            tidal_count += 1
        if log_df_no_dupes.iloc[i]['gate_2'] == "Tidal":
            tidal_count += 1
        if log_df_no_dupes.iloc[i]['gate_3'] == "Tidal":
            tidal_count += 1

        if tidal_count > 0:
            schism_gate_th.iloc[i, schism_gate_th.columns.get_loc('op_down')] = tidal_count/ndup
            schism_gate_th.iloc[i, schism_gate_th.columns.get_loc('op_up')] = 0.0
        else:
            schism_gate_th.iloc[i, schism_gate_th.columns.get_loc('op_down')] = open_count/ndup
            schism_gate_th.iloc[i, schism_gate_th.columns.get_loc('op_up')] = open_count/ndup
    schism_gate_th['op_down'] = schism_gate_th['op_down'].round(2)
    schism_gate_th['op_up'] = schism_gate_th['op_up'].round(2)

     ## save schism_gate_th, schism_fb_th and schism_bl_th to dest folder
    os.chdir(dest)  
    schism_gate_th.to_csv("smscg_radial.th", header=True, index=True)
    schism_fb_th.to_csv("smscg_flash.th", header=True, index=True)
    schism_bl_th.to_csv("smscg_boat_lock.th", header=True, index=True)



if __name__ == "__main__":
    smscg_log_2_schism_th()