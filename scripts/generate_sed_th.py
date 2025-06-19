import pandas as pd
import os
import sys
import datetime as dt

import schimpy.station as station
from schimpy import batch_metrics
from vtools.data.vtime import days, hours


# Linear relationship to convert turbidity to ssc
def turb_to_ssc_linear(df_turb, m: float, b: float):

    ssc = m * df_turb + b

    return ssc


# Power relationship to convert turbidity to ssc
def turb_to_ssc_power(df_turb, c: float, p: float):

    ssc = c * df_turb**p

    return ssc


#########################################################################
# Housekeeping
#########################################################################

# "Slope" and "intercept" for converting Turbidity to SSC using power relationship
constant_default = 0.00
power_default = 0.1

constants = {
    "sacramento": constant_default,
    "sjr": constant_default,
    "mokelumne": 4.43,
    "american": constant_default,
    "yolo": constant_default,
    "yolo_toedrain": constant_default,
}

powers = {
    "sacramento": power_default,
    "sjr": power_default,
    "mokelumne": 0.592,
    "american": power_default,
    "yolo": power_default,
    "yolo_toedrain": power_default,
}

# Prescribe the composition ratios of the sediment classes, whose sum should be 1.
composition = {
    "SED_1": 0.8,
    "SED_2": 0.15,
    "SED_3": 0.05,
}

# Specify bc locations to link them to obs stations
# Location with "None" indicate obs data is not available
bc_loc_to_stn = {
    "sacramento": "fpt",
    "sjr": "sjr",
    "mokelumne": "dlc",
    "american": None,
    "yolo": "lib",
    "yolo_toedrain": "lis",
}

# Define parameters for the batch metrics object
params = {
    "stations_csv": "./inputs/station_dbase.csv",
    "obs_links_csv": "./inputs/obs_links_20230315.csv",
    "obs_search_path": ["/scratch/nasbdo/modeling_data/repo/continuous/screened"],
}

db_stations = station.read_station_dbase(params["stations_csv"])
db_obs = station.read_obs_links(params["obs_links_csv"])

dt_start = dt.datetime(2021, 1, 1, 0, 0)
dt_end = dt.datetime(2024, 1, 1, 0, 0)

# List of locations with manually entered data
bc_manual = ["american"]

# List of locations with ssc timeseries available.
bc_ssc_th = []

# %%
# Create an empty dataframe to store the observed turbidity
df_all = pd.DataFrame()

# Create a batch metrics object
self = batch_metrics.BatchMetrics(params)
for loc in list(bc_loc_to_stn.keys()):
    print(f"Processing {loc}")
    if loc in bc_ssc_th:  # Read ssc data directly from file
        print("   SSC time series read directly from file")
        pass

    elif loc in bc_manual:  # Read ssc data from file or manually prescribe
        print("   SSC time series manually prescribed")
        df_all[loc] = 0.0099

    else:  # Convert FNU to SSC from observed data
        print("   SSC time series calculated from observed turbidity")
        turb_obs = self.retrieve_ts_obs(
            bc_loc_to_stn[loc],
            "default",
            "turbidity",
            [dt_start, dt_end],
            db_stations,
            db_obs,
        )

        # Save observed turbidity to file for reference
        turb_obs.to_csv(loc + ".csv")

        # Check for NaNs
        if turb_obs.isnull().values.any():

            # To do: Decide what to do with NaNs (interpolate?)
            # For now, fill NaNs with previous value
            turb_obs.ffill(inplace=True)

        # Convert turbidity to SSC
        ssc_calc = turb_to_ssc_power(turb_obs, constants[loc], powers[loc])
        ssc_calc.rename(loc, inplace=True)

        # Append to the total dataframe
        df_all = pd.concat([df_all, ssc_calc], axis=1)

# Convert index to seconds
df_all.index = (pd.to_datetime(df_all.index) - dt_start).total_seconds()

# Specify index precision
df_all.index = df_all.index.map(lambda x: "%.1f" % x)

# Save to file for each sediment class
for sedclass in composition:
    (df_all * composition[sedclass]).to_csv(
        sedclass + ".th", header=False, sep="\t", float_format="%.3e"
    )
