#!/usr/bin/env python
# coding: utf-8

# Script to create an elev2D.th.nc combining the NOAA water level data and
# prediction.

# Import Python packages
import pandas as pd

# import click
import dms_datastore.process_station_variable
import dms_datastore.download_noaa
import dms_datastore.read_ts
import schimpy.gen_elev2d
import schimpy.separate_species


# Commented out the command line arguments for now.
# @click.command()
# @click.option(
#     "--start_date",
#     type=str,
#     help="Start date of the simulation",
#     required=True,
#     default="2024-10-17",
# )
# @click.option("--end_date", type=str, help="End date of the simulation", required=True)
# @click.option(
#     "--subtidal_year", type=int, help="Subtidal year of the simulation", default=None
# )
def main():
    # Set some parameters here.
    download_period_past = {"begin": "2016-09-01", "end": "2017-02-01"}
    download_period_now = {"begin": "2024-09-01", "end": "2025-02-01"}
    fpath_elev2d = "elev2D.th.nc"
    start_elev2d = "2024-10-17"
    end_elev2d = "2025-01-01"
    slr = 0.0

    download_periods = [download_period_past, download_period_now]

    # t_stitch = pd.to_datetime("2024-11-01")

    # Two stations to generate the ocean water level boundary, Point Reyes and
    # Monterey.
    stations = [
        {"name": "Point Reyes", "station_id": "9415020"},
        {"name": "Monterey", "station_id": "9413450"},
    ]

    # Download the data from NOAA
    product = "water_level"

    noaa_stations = dms_datastore.process_station_variable.process_station_list(
        [s["station_id"] for s in stations], param="water_level"
    )
    noaa_stations["src_var_id"] = "water_level"
    noaa_stations["name"] = [s["name"] for s in stations]

    for period in download_periods:
        start = pd.to_datetime(period["begin"])
        end = pd.to_datetime(period["end"])
        dms_datastore.download_noaa.noaa_download(
            noaa_stations, ".", start, end, overwrite=True
        )

    # Download the prediction data from NOAA
    # NOTE Lots of quick coding here like reusing variables for now.
    noaa_stations["param"] = "predictions"
    noaa_stations["src_var_id"] = "predictions"
    start = pd.to_datetime(download_period_now["begin"])
    end = pd.to_datetime(download_period_now["end"])
    dms_datastore.download_noaa.noaa_download(
        noaa_stations, ".", start, end, overwrite=True
    )

    start_year_now = pd.to_datetime(download_period_now["begin"]).year
    end_year_now = pd.to_datetime(download_period_now["end"]).year
    start_year_past = pd.to_datetime(download_period_past["begin"]).year
    end_year_past = pd.to_datetime(download_period_past["end"]).year
    for station in stations:
        station_id = station["station_id"]

        # Read the historic tide for this year
        path_obs_cur = f"noaa_{station_id}_{station_id}_{product}_{start_year_now}_{end_year_now}.csv"
        df_cur = dms_datastore.read_ts.read_ts(path_obs_cur)

        # Read the historic tides from the past
        start_year_past = 2016
        path_obs_past = f"noaa_{station_id}_{station_id}_{product}_{start_year_past}_{end_year_past}.csv"
        df_past = dms_datastore.read_ts.read_ts(path_obs_past)

        # Read the tide prediction
        path_pred = f"noaa_{station_id}_{station_id}_predictions_{start_year_now}_{end_year_now}.csv"
        df_pred = dms_datastore.read_ts.read_ts(path_pred)
        df_pred_renamed = df_pred.rename(columns={"Prediction": "Water Level"})

        df_stitched = stitch_station(df_cur, df_past, df_pred_renamed)
        path_out = f"{station_id}_stitched.csv"
        df_stitched.to_csv(path_out)

    # Need to change the format slightly.
    # NOTE This needs to be done in the previous step.
    for station in stations:
        station_id = station["station_id"]
        path_in = f"{station_id}_stitched.csv"
        df = pd.read_csv(path_in, index_col="Date Time", parse_dates=["Date Time"])
        path_out = f"{station_id}_stitched_noaa.txt"
        with open(path_out, "w") as f:
            f.write(
                "# agency: noaa\n#\n#\n#\n#\n#\n#\nDate Time, Water Level, Sigma, O or I (for verified), F, R, L, Quality\n"
            )
            for i, row in df.iterrows():
                buf = f"{i.strftime('%Y%m%d %H:%M')},{row['Water Level']}\n"
                f.write(buf)

    # Generate elev2D file.
    hgrid_fpath = "hgrid.gr3"
    pt_reyes_fpath = "9415020_stitched_noaa.txt"
    monterey_fpath = "9413450_stitched_noaa.txt"
    schimpy.gen_elev2d.gen_elev2D(
        hgrid_fpath,
        fpath_elev2d,
        pt_reyes_fpath,
        monterey_fpath,
        start_elev2d,
        end_elev2d,
        slr
    )


def stitch_station(df_cur, df_past, df_pred, t_stitch=None):
    """Stitch the historical water lever with the prediction one

    Parameters
    ----------
    df_cur : pd.DataFrame
        The current historical data
    df_past : pd.DataFrame
        The past historical data
    df_pred : pd.DataFrame
        The prediction data
    t_transition : datetime, optional
        The time of transition between the historical and prediction data
    """

    # Hardcode some variables
    name_y = "Water Level"

    if t_stitch is None:
        t_stitch = df_cur.iloc[-1].name
    year_to_stich_in_past = df_past.index[0].year
    t_stich_past = pd.to_datetime(
        f"{year_to_stich_in_past}-{t_stitch.month}-{t_stitch.day} {t_stitch.hour}:{t_stitch.minute}"
    )

    df_subtidal_past = schimpy.separate_species.separate_species(df_past)[0]

    # Add the historial subtidal information to the prediction.
    # - Extra mean tide will be remove below by subtracting the difference at a transition point.
    # - Need to trim the data due to possible leap days
    length = min(len(df_pred[t_stitch:]), len(df_subtidal_past[t_stich_past:]))
    pred_plus_subtidal = (
        df_pred[t_stitch:][name_y].values[:length]
        + df_subtidal_past[t_stich_past:][name_y].values[:length]
    )
    # Calculate the difference at the transition point
    diff_at_t_transition = pred_plus_subtidal[0] - df_cur.loc[t_stitch][name_y]

    # Shift the whole prediction series by the amount of the difference.
    df_pred_plus_subtidal = pd.DataFrame(
        data={
            "Date Time": df_pred[t_stitch:].index[1:length],
            "Water Level": (pred_plus_subtidal - diff_at_t_transition)[1:length],
        }
    ).set_index("Date Time")
    return pd.concat((df_cur[:t_stitch], df_pred_plus_subtidal))


if __name__ == "__main__":
    main()
