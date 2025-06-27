from schimpy.th_calcs import calc_net_source_sink, combine_flux, read_flux
from schimpy.model_time import is_elapsed
from vtools.functions.interpolate import rhistinterp
from bdschism.calc_ndoi import calc_indoi
import schimpy.param as parms
from itertools import cycle
import pandas as pd
import xarray as xr
import numpy as np
import datetime as dt
import click
import os

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

bds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")

boundary_list = [
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
    "dcu",
    "tide",
    "ndo",
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
    "tide": ["tide"],
    "gate": ["dcc", "smscg_radial", "smscg_flash", "smscg_boat"],
}


def get_required_files(flux_file, vsource_file, vsink_file, elev2d_file, boundary_list):
    """Get the required files for boundary data."""
    files = []
    if "tide" in boundary_list:
        files.append(elev2d_file)
    if "dcu" in boundary_list:
        files.append(vsource_file)
        files.append(vsink_file)
    if "flux" in boundary_list or any(b in bc_types["flux"] for b in boundary_list):
        files.append(flux_file)
    if any(b in bc_types["gate"] for b in boundary_list):
        print("Gate data not implemented yet, skipping...")
    if not files:
        raise ValueError("No valid boundary types provided in boundary_list.")

    return files


def get_observed_data(
    bds_dir=bds_dir, boundary_list=[b for b in boundary_list if b != "tide"]
):
    """Get observed data from the BDS directory, excluding 'tide'."""

    print(f"Getting observed data from BDS directory {bds_dir} (excluding 'tide')...")
    obs_df = get_boundary_data(
        flux_file=os.path.join(bds_dir, "data/time_history/flux.th"),
        vsource_file=os.path.join(bds_dir, "data/channel_depletion/vsource_dated.th"),
        vsink_file=os.path.join(bds_dir, "data/channel_depletion/vsink_dated.th"),
        elev2d_file=os.path.join(bds_dir, "data/elev2D.th.nc"),
        elapsed_unit="s",
        out_freq="15min",
        boundary_list=boundary_list,
    )

    return obs_df


def get_boundary_data(
    flux_file="flux.th",
    vsource_file="vsource.th",
    vsink_file="vsink.th",
    elev2d_file="elev2D.th.nc",
    time_basis=None,
    rndays=None,
    elapsed_unit="s",
    out_freq="15min",
    flux_head=os.path.join(bds_dir, "./data/time_history/flux.th"),
    sink_head=os.path.join(bds_dir, "./data/channel_depletion/vsink_dated.th"),
    source_head=os.path.join(bds_dir, "./data/channel_depletion/vsource_dated.th"),
    boundary_list=boundary_list,
):
    """Get a DataFrame of boundary data from flux, vsource, vsink, and elev2D.th.nc files."""

    print(f"Getting boundary data from {os.getcwd()}...")
    # Check if the files exist
    files = get_required_files(
        flux_file=flux_file,
        vsource_file=vsource_file,
        vsink_file=vsink_file,
        elev2d_file=elev2d_file,
        boundary_list=boundary_list,
    )
    elapsed_files = []
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"File {f} does not exist.")

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
        dcu_df = rhistinterp(dcu_df, out_freq)
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

        out_df["ndo"] = rhistinterp(ndoi_df, out_freq)
    # Get the tidal boundary condition data
    if "tide" in boundary_list:
        elev_df = xr.open_dataset(
            elev2d_file
        )  # shape is elev_df.time_series[timesteps, nOpenBndNodes, nLevels, nComponents]

        tidal_bc = elev_df.time_series.mean(
            dim=["nOpenBndNodes", "nLevels", "nComponents"]
        )
        tidal_bc_series = tidal_bc.to_series()

        # Convert DatetimeIndex to PeriodIndex
        tidal_bc_series.index = tidal_bc_series.index.to_period()

        out_df["tide"] = rhistinterp(tidal_bc_series, out_freq)

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
        flux_df = rhistinterp(flux_df, out_freq)
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
        out_df = pd.concat([out_df, flux_df], axis=1)

    # Get gate data
    if any(b in bc_types["gate"] for b in boundary_list):
        print("\tGate data not implemented yet, skipping...")

    print("Done Collecting boundary data.\n\n")

    return out_df


# # Extract scenario name by removing the suffix matching one of cols_to_keep
# def get_scenario_name(col):
#     for suffix in cols_to_keep:
#         if col.endswith(suffix):
#             return col[: -len(suffix) - 1]  # remove "_" + suffix
#     return col


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

    # If no columns to keep are specified, use all columns except the index
    if cols_to_keep is None:
        cols_to_keep = [
            col
            for col in bc_data_list[0].columns
            if col not in ["time", "date", "datetime"]
        ]
    else:
        print(f"Plotting using specified columns: {cols_to_keep}")

    # Ensure all DataFrames have the same columns
    for bc_data in bc_data_list:
        missing_cols = set(cols_to_keep) - set(bc_data.columns)
        if missing_cols:
            raise ValueError(f"DataFrame is missing columns: {missing_cols}")

    # Create subplots
    fig = make_subplots(
        rows=len(cols_to_keep),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(cols_to_keep),
    )

    print("Generating boundary data plots...")
    # Loop through each DataFrame in the list
    for bc_data, scenario in zip(bc_data_list, scenario_names):
        # Take only the columns that are in cols_to_keep
        bc_data = bc_data[cols_to_keep]
        row = 0  # Initialize row index for subplot
        for i, col in enumerate(bc_data.columns):
            row = i + 1
            color = color_map.get(scenario, "gray")
            show_legend = i == 0
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
        height=1500,
        title_text="Model Boundary Time Series",
        showlegend=True,
        hoversubplots="axis",
        hovermode="x unified",
    )

    # Update y-axes and x-axes titles
    for i in range(1, len(cols_to_keep) + 1):
        fig.update_yaxes(title_text="Flow (cfs)", row=i, col=1)
        fig.update_xaxes(title_text="", row=i, col=1)

    fig.update_xaxes(showspikes=True, spikecolor="black", spikethickness=1)
    fig.update_yaxes(showspikes=True, spikecolor="black", spikethickness=1)

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
def plot_bds_bc_cli(obs, sim_dirs, scenario_names, html_name):
    """
    CLI to plot boundary data from observed and/or simulation directories.
    """
    os.chdir(sim_dirs[0])  # Ensure cwd is correct

    bc_data_list = []
    scenario_list = []

    # Observed data
    if obs:
        obs_data = get_observed_data()
        bc_data_list.append(obs_data)
        scenario_list.append("Observed")

    # Simulation data
    for i, sim_dir in enumerate(sim_dirs):
        sim_dir = os.path.abspath(sim_dir)
        os.chdir(sim_dir)
        bc_data = get_boundary_data()
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
    plot_bds_bc_cli()
