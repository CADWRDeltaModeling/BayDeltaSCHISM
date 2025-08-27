import os
import shutil
import datetime as dt
from itertools import cycle
import logging

import pandas as pd
import numpy as np
import xarray as xr

import click

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from schimpy.th_calcs import (
    calc_net_source_sink,
    combine_flux,
    read_flux,
    struct_open_props,
)
from schimpy.model_time import read_th, is_elapsed
import schimpy.param as parms
from schimpy.schism_structure import SchismStructureIO as Struct
from schimpy.prepare_schism import get_structures_from_yaml
from schimpy.schism_input import *
from schimpy.util.yaml_load import yaml_from_file

from vtools.functions.interpolate import rhistinterp
from vtools.functions.unit_conversions import CMS2CFS, M2FT

import dms_datastore.process_station_variable
import dms_datastore.download_noaa
import dms_datastore.read_ts

from bdschism.calc_ndoi import calc_indoi

bds_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")
)

boundary_list = [
    "tide",
    "ccc_rock",
    "ccc_old",
    "ccc_victoria",
    "swp",
    "cvp",
    "ccfb_gate",
    "dcu",
    "ndo",
    "exports",
    "sac",
    "american",
    "yolo_toedrain",
    "yolo",
    "east",
    "calaveras",
    "northbay",
    "delta_cross_channel",
    "montezuma_radial",
    "montezuma_flash",
    "montezuma_boat_lock",
    "grantline_barrier",
    "midr_culvert_l",
    "midr_culvert_r",
    "midr_weir",
    "oldr_head_barrier",
    # "oldr_tracy_culvert",
    # "oldr_tracy_weir",
    # "tom_paine_sl_culvert",
    # "west_false_river_barrier_leakage",
]

bc_types = {
    "flux": [
        "sac",
        "american",
        "yolo_toedrain",
        "yolo",
        "east",
        "calaveras",
        "northbay",
        "ccc_rock",
        "ccc_old",
        "ccc_victoria",
        "swp",
        "cvp",
    ],
    "dcu": ["dcu"],
    "exports": ["exports"],
    "tide": ["tide"],
    "gate": [
        "delta_cross_channel",
        "montezuma_radial",
        "montezuma_flash",
        "montezuma_boat_lock",
        "ccfb_gate",
        "grantline_barrier",
        "grantline_culvert",
        "grantline_weir",
        "midr_culvert_l",
        "midr_culvert_r",
        "midr_weir",
        "oldr_head_barrier",
        "oldr_tracy_culvert",
        "oldr_tracy_weir",
        "tom_paine_sl_culvert",
        "west_false_river_barrier_leakage",
    ],
}


def get_required_files(
    flux_file,
    vsource_file,
    vsink_file,
    elev2d_file,
    boundary_list,
    struct_fn="hydraulics.in",
    gate_dir="./",
    gate_suffix="",
):
    """Get the required files for boundary data."""
    files = []
    if "tide" in boundary_list:
        files.append(elev2d_file)
    if ("dcu" in boundary_list) or ("ndoi" in boundary_list):
        files.append(vsource_file)
        files.append(vsink_file)
    if (
        "flux" in boundary_list
        or any(b in bc_types["flux"] for b in boundary_list)
        or ("exports" in boundary_list)
    ):
        files.append(flux_file)
    if any(b in bc_types["gate"] for b in boundary_list):
        files.append(struct_fn)
        for gfn in bc_types["gate"]:
            if gfn in boundary_list:
                if gate_suffix == "":
                    files.append(f"{gate_dir}/{gfn}{gate_suffix}.th")
                else:
                    files.append(f"{gate_dir}/{gfn}.{gate_suffix}.th")
    if not files:
        raise ValueError("No valid boundary types provided in boundary_list.")

    return files


def get_observed_data(
    bds_dir=bds_dir,
    boundary_list=boundary_list,
    period={"begin": "2016-09-01", "end": "2025-02-01"},
    out_freq="1D",
):
    """Get observed data from the BDS directory, then get tidal data from noaa download."""

    print(f"Getting observed data from BDS directory {bds_dir} (excluding 'tide')...")
    obs_df = get_boundary_data(
        flux_file=os.path.join(bds_dir, "data/time_history/flux.th"),
        vsource_file=os.path.join(bds_dir, "data/channel_depletion/vsource_dated.th"),
        vsink_file=os.path.join(bds_dir, "data/channel_depletion/vsink_dated.th"),
        elev2d_file=os.path.join(bds_dir, "data/elev2D.th.nc"),
        gate_dir=os.path.join(bds_dir, "data/time_history/"),
        elapsed_unit="s",
        out_freq=out_freq,
        boundary_list=[b for b in boundary_list if b != "tide"],
        time_basis=pd.to_datetime(period["begin"]),
        rndays=int(
            (pd.to_datetime(period["end"]) - pd.to_datetime(period["begin"])).days
        ),
        struct_fn=os.path.join(
            bds_dir, "templates/bay_delta/hydraulic_structures.yaml"
        ),
        obs=True,
    )

    print(f"\tGetting observed tidal data from NOAA...")
    if "tide" in boundary_list:
        tide_df = get_observed_tide(period=period) * M2FT
        tide_df.index = tide_df.index.to_period()

        obs_df["tide"] = rhistinterp(tide_df.mean(axis=1), out_freq, p=100)

    return obs_df


def get_observed_tide(
    period={"begin": "2016-09-01", "end": "2025-02-01"},
):
    # Set some parameters here.

    # Two stations to generate the ocean water level boundary, Point Reyes and
    # Monterey.
    stations = [
        {"name": "Point Reyes", "station_id": "9415020"},
        {"name": "Monterey", "station_id": "9413450"},
    ]

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

    start = pd.to_datetime(period["begin"])
    start_year = pd.to_datetime(period["begin"]).year
    end = pd.to_datetime(period["end"])
    end_year = pd.to_datetime(period["end"]).year
    dms_datastore.download_noaa.noaa_download(
        noaa_stations, "./tempdeletenoaa", start, end, overwrite=True
    )

    df_list = []
    for station in stations:
        station_id = station["station_id"]

        # Read the data and delete the file
        fname = f"./tempdeletenoaa/noaa_{station_id}_{station_id}_{product}_{start_year}_{end_year}.csv"
        df = dms_datastore.read_ts.read_ts(fname)
        os.remove(fname)
        # Rename the value column to the station_id
        df = df.rename(columns={df.columns[0]: station_id})
        df_list.append(df)
    shutil.rmtree("./tempdeletenoaa")

    # Merge all DataFrames on the index (Date Time)
    df_tide_bc = pd.concat(df_list, axis=1)

    return df_tide_bc


def get_date_data(
    gate_name,
    structures,
    gate_fn="{gate_name}.th",
    gate_head=os.path.join(bds_dir, "./data/time_history/{gate_name}.th"),
    time_basis=None,
    elapsed_unit="s",
    out_freq="1D",
    datetime_idx=None,
):
    if isinstance(structures[0], dict):
        struct = next(
            (s for s in structures if s["name"] == gate_name), None
        )  # structure object that corresponds to gate_name
    else:
        struct = next(
            (s for s in structures if s.name == gate_name), None
        )  # structure object that corresponds to gate_name

    if struct is None:
        raise ValueError(f"{gate_name} is not found in hydraulics.in file...")

    th_data = read_th(
        gate_fn.format(),
        time_basis=time_basis,
        elapsed_unit=elapsed_unit,
        head=gate_head,
    )
    up_df, down_df = struct_open_props(
        struct,
        th_data,
        out_freq=out_freq,
        datetime_idx=datetime_idx,
    )

    return up_df, down_df


def get_boundary_data(
    flux_file="flux.th",
    vsource_file="vsource.th",
    vsink_file="vsink.th",
    elev2d_file="elev2D.th.nc",
    gate_dir="./",
    gate_suffix="",
    time_basis=None,
    rndays=None,
    elapsed_unit="s",
    out_freq="1D",
    flux_head=os.path.join(bds_dir, "./data/time_history/flux.th"),
    sink_head=os.path.join(bds_dir, "./data/channel_depletion/vsink_dated.th"),
    source_head=os.path.join(bds_dir, "./data/channel_depletion/vsource_dated.th"),
    boundary_list=boundary_list,
    struct_fn="hydraulics.in",
    obs=False,
):
    """Get a DataFrame of boundary data from flux, vsource, vsink, and elev2D.th.nc files."""

    if not obs:
        print(f"Getting boundary data from {os.getcwd()}...")
    # Check if the files exist
    files = get_required_files(
        flux_file=flux_file,
        vsource_file=vsource_file,
        vsink_file=vsink_file,
        elev2d_file=elev2d_file,
        boundary_list=boundary_list,
        struct_fn=struct_fn,
        gate_dir=gate_dir,
        gate_suffix=gate_suffix,
    )
    elapsed_files = []
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"File {os.path.abspath(f)} does not exist.")

    # Check if the files are elapsed or datetime stamped
    elapsed_files = [
        is_elapsed(f)
        for f in [flux_file, vsource_file, vsink_file]
        if isinstance(f, str)
    ]

    # Determine time_basis and rndays from param.nml if not provided
    if time_basis is None:
        params = parms.read_params("./param.nml")
        time_basis = params.run_start
        print(
            f"\t\tSince no time_basis provided, inferring from param.nml:\n\t\t{os.path.abspath('./param.nml')}"
        )
    if rndays is None:
        params = parms.read_params("./param.nml")
        rndays = params["rnday"]
        print(
            f"\t\tSince no rndays provided, inferring from param.nml:\n\t\t{os.path.abspath('./param.nml')}"
        )
    end_date = time_basis + dt.timedelta(days=rndays)

    out_idx = pd.date_range(
        start=time_basis,
        end=end_date,
        freq=out_freq,
    )

    out_df = pd.DataFrame(index=out_idx)

    # Handle DCU and NDO boundaries
    if any(b in boundary_list for b in ["dcu", "ndo"]):
        dcu_df, src, sink = calc_net_source_sink(
            vsource_file=vsource_file,
            vsink_file=vsink_file,
            time_basis=time_basis,
            elapsed_unit=elapsed_unit,
            vsource_head=source_head,
            vsink_head=sink_head,
            search_term="delta",
        )
        dcu_df.index = dcu_df.index.to_period()
        dcu_df = rhistinterp(dcu_df, out_freq, p=100)
        # Convert to cfs
        dcu_df = dcu_df * CMS2CFS

        out_df["dcu"] = dcu_df
    if "ndo" in boundary_list:
        ndoi_df = calc_indoi(
            flux_file=flux_file,
            vsource_file=vsource_file,
            vsink_file=vsink_file,
            time_basis=time_basis,
            elapsed_unit=elapsed_unit,
            source_head=source_head,
            sink_head=sink_head,
            flux_head=flux_head,
        )
        # Convert DatetimeIndex to PeriodIndex
        ndoi_df.index = ndoi_df.index.to_period()

        # Convert to cfs
        ndoi_df = ndoi_df * CMS2CFS

        out_df["ndo"] = rhistinterp(ndoi_df, out_freq, p=100)
    # Get the tidal boundary condition data
    if "tide" in boundary_list:
        print("\tReading tidal boundary")
        elev_df = xr.open_dataset(
            elev2d_file
        )  # shape is elev_df.time_series[timesteps, nOpenBndNodes, nLevels, nComponents]

        tidal_bc = elev_df.time_series.mean(
            dim=["nOpenBndNodes", "nLevels", "nComponents"]
        )
        tidal_bc_series = tidal_bc.to_series()

        # Convert DatetimeIndex to PeriodIndex
        tidal_bc_series.index = tidal_bc_series.index.to_period()

        # Convert to ft
        tidal_bc_series = tidal_bc_series * M2FT

        out_df["tide"] = rhistinterp(tidal_bc_series, out_freq, p=100)

    # Get the flux data
    if any(b in bc_types["flux"] for b in boundary_list) | ("flux" in boundary_list):
        flux_df = read_flux(
            flux=flux_file,
            flux_head=flux_head,
            time_basis=time_basis,
            elapsed_unit=elapsed_unit,
            start_date=time_basis,
            end_date=end_date,
        )
        flux_df.index = flux_df.index.to_period()
        flux_df = rhistinterp(flux_df, out_freq, p=100)
        # Subset the flux DataFrame to only the boundaries in boundary_list
        if "flux" in boundary_list:
            flux_df = flux_df[
                [
                    col
                    for col in flux_df.columns
                    if any(b in col for b in bc_types["flux"])
                ]
            ]
        else:
            flux_df = flux_df[[col for col in flux_df.columns if col in boundary_list]]

        # Convert to cfs
        flux_df = flux_df * CMS2CFS

        out_df = pd.concat([out_df, flux_df], axis=1)

    # Get gate data
    if any(b in bc_types["gate"] for b in boundary_list):
        if struct_fn.endswith(".in"):
            schinp = SchismInput(None)
            structure_reader = Struct(schinp)
            structure_reader.read(struct_fn)

            structures = schinp.structures
        elif struct_fn.endswith(".yaml"):
            struct_inp = yaml_from_file(struct_fn)
            struct_inp = struct_inp.get("structures")
            structures = get_structures_from_yaml(struct_inp)

        for gfn in [g for g in bc_types["gate"] if g in boundary_list]:
            print(f"\t\tGetting gate {gfn}..")
            if gate_suffix == "":
                gate_fn = f"{gfn}{gate_suffix}.th"
            else:
                gate_fn = f"{gfn}.{gate_suffix}.th"
            up_df, down_df = get_date_data(
                gfn,
                structures,
                gate_fn=os.path.join(gate_dir, gate_fn),
                gate_head=os.path.join(bds_dir, f"./data/time_history/{gfn}.th"),
                time_basis=time_basis,
                elapsed_unit=elapsed_unit,
                out_freq=out_freq,
                datetime_idx=out_idx,
            )
            out_df[f"{gfn}_up"] = up_df
            out_df[f"{gfn}_down"] = down_df

    print("Done collecting boundary data.\n\n")

    return out_df


def plot_bds_boundaries(
    bc_data_list,
    scenario_names,
    cols_to_keep=None,
    write_html=True,
    html_name="bds_input_boundaries.html",
):
    """Plot the boundary data from the DataFrame."""

    # Plot the merged DataFrame
    # Two panels with x-axis aligned as date, color by experiment name
    # Assign unique colors per scenario
    palette = px.colors.qualitative.Set2
    color_cycle = cycle(palette)  # infinite cycling

    color_map = {scenario: next(color_cycle) for scenario in sorted(scenario_names)}
    color_map["Observed"] = "gray"

    # If no columns to keep are specified, use all columns except the index
    if cols_to_keep is None:
        # Get all columns in the first DataFrame
        data_cols = set(bc_data_list[0].columns)
        # Include items from boundary_list that are present as columns
        cols_to_keep = [b for b in boundary_list if b in data_cols]
        # Also include _up/_down variants if present
        for b in boundary_list:
            for suffix in ["_up", "_down"]:
                colname = f"{b}{suffix}"
                if colname in data_cols and colname not in cols_to_keep:
                    cols_to_keep.append(colname)
    else:
        print(f"Plotting using specified columns: {cols_to_keep}")

    # Ensure all DataFrames have the same columns
    for bc_data in bc_data_list:
        missing_cols = set(cols_to_keep) - set(bc_data.columns)
        if missing_cols:
            raise ValueError(f"DataFrame is missing columns: {missing_cols}")

    # group structures by name (up and down on same subplot
    # Unique base names, preserving order
    seen = set()
    subplot_names = []
    for col in cols_to_keep:
        base = col.replace("_up", "").replace("_down", "")
        if base not in seen:
            subplot_names.append(base)
            seen.add(base)
    # Sort according to boundary_list
    subplot_names = [b for b in boundary_list if b in subplot_names]

    # Create subplots
    fig = make_subplots(
        rows=len(subplot_names),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.01,
        subplot_titles=(subplot_names),
    )

    print("Generating boundary data plots...")
    # Loop through each DataFrame in the list
    for bc_data, scenario in zip(bc_data_list, scenario_names):
        # Take only the columns that are in cols_to_keep
        bc_data = bc_data[cols_to_keep]
        row = 0  # Initialize row index for subplot
        for i, col in enumerate(subplot_names):
            row = i + 1
            color = color_map.get(scenario, "gray")
            show_legend = i == 0
            if col in bc_types["gate"]:
                # Plot both upstream and downstream operations
                trace_up = go.Scatter(
                    x=bc_data.index,
                    y=bc_data[f"{col}_up"],
                    name=scenario,
                    line=dict(color=color),
                    hovertemplate=f"{scenario}<br>%{{y:.2f}} upstream<extra></extra>",
                    showlegend=show_legend,  # Hide the legend
                    legendgroup=scenario,
                )
                fig.add_trace(trace_up, row=row, col=1)
                trace_down = go.Scatter(
                    x=bc_data.index,
                    y=bc_data[f"{col}_down"],
                    name=scenario,
                    line=dict(color=color),
                    hovertemplate=f"{scenario}<br>%{{y:.2f}} downstream<extra></extra>",
                    showlegend=False,  # Hide the legend
                    legendgroup=scenario,
                )
                fig.add_trace(trace_down, row=row, col=1)
            else:
                trace = go.Scatter(
                    x=bc_data.index,
                    y=bc_data[col],
                    name=scenario,
                    line=dict(color=color),
                    hovertemplate=f"{scenario}<br>%{{y:.2f}} cfs<extra></extra>",
                    showlegend=show_legend,  # Hide the legend
                    legendgroup=scenario,
                )
                fig.add_trace(trace, row=row, col=1)

    # Update layout
    fig.update_layout(
        height=4000,
        title_text="Model Boundary Time Series",
        showlegend=True,
        hoversubplots="axis",
        hovermode="x unified",
        plot_bgcolor="#f5f5f5",  # <-- Pale/white background
    )

    # Update y-axes and x-axes titles
    for i, col in enumerate(subplot_names):
        if (col in bc_types["flux"]) or (col in ["ndo", "dcu"]):
            fig.update_yaxes(title_text="Flow (cfs)", row=i + 1, col=1)
        elif col in bc_types["gate"]:
            fig.update_yaxes(
                title_text="Gate Opening",
                row=i + 1,
                col=1,
                tickvals=[-1, 0, 1],
                ticktext=["Downstream Open", "Closed", "Upstream Open"],
            )
        elif col == "tide":
            fig.update_yaxes(title_text="Stage (ft)", row=i + 1, col=1)

    fig.update_xaxes(
        showspikes=True,
        spikecolor="black",
        spikethickness=1,
        showgrid=True,
        gridcolor="lightgrey",  # Major gridlines
        zeroline=False,
        minor=dict(showgrid=True, gridcolor="gainsboro"),  # Minor gridlines
        title_text="",
    )
    fig.update_yaxes(
        showspikes=True,
        spikecolor="black",
        spikethickness=1,
        showgrid=True,
        gridcolor="lightgrey",  # Major gridlines
        zeroline=True,
        minor=dict(showgrid=True, gridcolor="gainsboro"),  # Minor gridlines
    )

    # Export to HTML
    if write_html:
        print(f"Exporting plot to HTML:\n{os.path.abspath(html_name)}")
        fig.write_html(html_name)
    else:
        fig.show()


@click.command()
@click.option(
    "-o",
    "--obs",
    is_flag=True,
    default=False,
    help="Include observed data in the plot.",
)
@click.option(
    "--sim-dirs",
    multiple=True,
    required=True,
    help="Simulation directories to get boundary data from. Can specify multiple.",
)
@click.option(
    "--scenario-names",
    multiple=True,
    default=None,
    help="Optional scenario names for each simulation directory. If not provided, uses the last folder name. Do not need to include 'Observed' for the observed data.",
)
@click.option(
    "--html-name",
    default="bds_input_boundaries.html",
    help="Output HTML plot filename.",
)
@click.option(
    "--out-freq",
    default="1D",
    help="Output data frequency. Default is one day.",
)
@click.argument("extra", nargs=-1)
@click.help_option("-h", "--help")
def plot_bds_bc_cli(obs, sim_dirs, scenario_names, html_name, out_freq, extra=()):
    """
    CLI to plot boundary data from observed and/or simulation directories.
    """
    # Parse extra arguments into a dictionary (expects --key value pairs)
    envvar = {}
    key = None
    for item in extra:
        if item.startswith("--"):
            key = item.lstrip("-")
        elif key is not None:
            envvar[key] = item
            key = None
    if key is not None:
        raise ValueError(f"No value provided for extra argument: {key}")
    envvar["out_freq"] = out_freq

    sim_dirs = [os.path.abspath(sim_dir) for sim_dir in sim_dirs]
    html_name = os.path.abspath(html_name)

    os.chdir(sim_dirs[0])  # Ensure cwd is correct
    # Determine time_basis and rndays from param.nml
    params = parms.read_params("./param.nml")
    time_basis = params.run_start
    rndays = params["rnday"]
    print(
        f"\t\tInferring run period from param.nml:\n\t\t{os.path.abspath('./param.nml')}"
    )
    end_date = time_basis + dt.timedelta(days=rndays)

    bc_data_list = []
    scenario_list = []

    # Observed data
    if obs:
        obs_data = get_observed_data(
            period={"begin": time_basis, "end": end_date}, **envvar
        )
        bc_data_list.append(obs_data)
        scenario_list.append("Observed")

    # Simulation data
    for i, sim_dir in enumerate(sim_dirs):
        os.chdir(sim_dir)
        # Pass envvar as keyword arguments to get_boundary_data
        bc_data = get_boundary_data(**envvar)
        bc_data_list.append(bc_data)
        if scenario_names and len(scenario_names) > i:
            scenario_list.append(scenario_names[i])
        else:
            scenario_list.append(os.path.basename(os.path.normpath(sim_dir)))

    # Plot
    plot_bds_boundaries(
        bc_data_list, scenario_list, write_html=True, html_name=html_name
    )


if __name__ == "__main__":
    # os.chdir("/scratch/projects/summer_x2_2025/simulations/")
    # sim_dirs = ["2016_noaction"]
    # html_name = "_test.html"

    # scenario_names = sim_dirs
    # sim_dirs = [os.path.abspath(sim_dir) for sim_dir in sim_dirs]
    # html_name = os.path.abspath(html_name)
    # os.chdir(sim_dirs[0])  # Ensure cwd is correct
    # params = parms.read_params("./param.nml")
    # time_basis = params.run_start
    # rndays = params["rnday"]
    # end_date = time_basis + dt.timedelta(days=rndays)
    # bc_data_list = []
    # scenario_list = []
    # envvar = {}
    # boundary_list = ["ccfb_gate"]  # boundary_list
    # # Observed data
    # if False:
    #     obs_data = get_observed_data(
    #         period={"begin": time_basis, "end": end_date},
    #         boundary_list=boundary_list,
    #         **envvar,
    #     )
    #     bc_data_list.append(obs_data)
    #     scenario_list.append("Observed")
    # # Simulation data
    # for i, sim_dir in enumerate(sim_dirs):
    #     os.chdir(sim_dir)
    #     # Pass envvar as keyword arguments to get_boundary_data
    #     bc_data = get_boundary_data(boundary_list=boundary_list, **envvar)
    #     bc_data_list.append(bc_data)
    #     if scenario_names and len(scenario_names) > i:
    #         scenario_list.append(scenario_names[i])
    #     else:
    #         scenario_list.append(os.path.basename(os.path.normpath(sim_dir)))
    # # Plot
    # plot_bds_boundaries(
    #     bc_data_list, scenario_list, write_html=True, html_name=html_name
    # )

    plot_bds_bc_cli()
