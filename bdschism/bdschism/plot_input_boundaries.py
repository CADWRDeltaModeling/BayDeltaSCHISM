from schimpy.th_calcs import calc_net_source_sink, combine_flux, read_flux
from schimpy.model_time import is_elapsed
import schimpy.param as parms
import pandas as pd
import datetime as dt
import click
import os

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from itertools import cycle

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
]


def get_boundary_data(
    flux_file="flux.th",
    vsource_file="vsource.th",
    vsink_file="vsink.th",
    elev2d_file="elev2d.th.nc",
    time_basis=None,
    rndays=None,
    elapsed_unit="s",
    out_freq="15m",
    flux_head=os.path.join(bds_dir, "./data/time_history/flux.th"),
    sink_head=os.path.join(bds_dir, "./data/channel_depletion/vsink_dated.th"),
    source_head=os.path.join(bds_dir, "./data/channel_depletion/vsource_dated.th"),
    boundary_list=boundary_list,
):
    """Get a DataFrame of boundary data from flux, vsource, vsink, and elev2d.th.nc files."""

    elapsed_files = [
        is_elapsed(f)
        for f in [flux_file, vsource_file, vsink_file]
        if isinstance(f, str)
    ]
    if time_basis is None and any(elapsed_files):
        params = parms.read_params("./param.nml")
        time_basis = params.run_start
        print(
            f"Since no time_basis provided, inferring from param.nml: {os.path.abspath('./param.nml')}"
        )
    if rndays is None:
        params = parms.read_params("./param.nml")
        rndays = params["rndays"]
        print(
            f"Since no rndays provided, inferring from param.nml: {os.path.abspath('./param.nml')}"
        )

    out_idx = pd.date_range(
        start=time_basis,
        end=time_basis + pd.timedelta(rndays),
        freq=out_freq,
    )
    out_df = pd.DataFrame(index=out_idx)

    if "dcu" in boundary_list:
        dcu_df, src, sink = calc_net_source_sink(
            vsource_file=vsource_file,
            vsink_file=vsink_file,
            time_basis=time_basis,
            elapsed_unit=elapsed_unit,
            vsource_head=source_head,
            vsink_head=sink_head,
            search_term="delta",
        )
        dcu_df = rhistinterp
        out_df["dcu"] = dcu_df
    elif "tide" in boundary_list:
        dcu_df = pd.DataFrame()

# Extract scenario name by removing the suffix matching one of cols_to_keep
def get_scenario_name(col):
    for suffix in cols_to_keep:
        if col.endswith(suffix):
            return col[: -len(suffix) - 1]  # remove "_" + suffix
    return col

def plot_bds_boundaries:
    
    # Plot the merged DataFrame
    # Two panels with x-axis aligned as date, color by experiment name
    # Assign unique colors per scenario
    unique_scenarios = {get_scenario_name(col) for col in merged_df.columns}

    palette = px.colors.qualitative.Set2
    color_cycle = cycle(palette)  # infinite cycling

    color_map = {scenario: next(color_cycle) for scenario in sorted(unique_scenarios)}
    # Create subplots
    fig = make_subplots(
        rows=len(cols_to_keep),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        # subplot_titles=("Net Delta Outflow In [cfs]", "Martinez Out [cfs]"),
        subplot_titles=(cols_to_keep),
    )
    # Track which scenarios we've already added to the legend
    seen_scenarios = set()

    for col in merged_df.columns:
        # Determine which metric this column belongs to
        for i, metric in enumerate(cols_to_keep):
            if col.endswith(metric):
                row = i + 1  # subplot row is 1-indexed
                scenario = get_scenario_name(col)
                color = color_map.get(scenario, "gray")

                show_legend = False
                if scenario not in seen_scenarios:
                    show_legend = True
                    seen_scenarios.add(scenario)

                trace = go.Scatter(
                    x=merged_df.index,
                    y=merged_df[col],
                    name=scenario,
                    line=dict(color=color),
                    hovertemplate=f"{scenario}<br>%{{y:.2f}} cfs<extra></extra>",
                    showlegend=show_legend,
                    legendgroup=scenario,
                )

                fig.add_trace(trace, row=row, col=1)
                break  # only one match per column

    # Update layout
    fig.update_layout(
        height=1500,
        title_text="Model Boundary Flow Time Series",
        showlegend=True,
        hovermode="x unified",
    )

    for i in range(1, len(cols_to_keep) + 1):
        fig.update_yaxes(title_text="Flow (cfs)", row=i, col=1)
        fig.update_xaxes(title_text="", row=i, col=1)

    # Export to HTML
    fig.write_html("ndo_plot.html")
