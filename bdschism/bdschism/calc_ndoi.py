from schimpy.th_calcs import calc_net_source_sink, combine_flux, read_flux
from schimpy.model_time import is_elapsed
import schimpy.param as parms
import pandas as pd
import click
import os

bds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../")


def calc_indoi(
    flux_file="flux.th",
    vsource_file="vsource.th",
    vsink_file="vsink.th",
    time_basis=None,
    elapsed_unit="s",
    flux_head=os.path.join(bds_dir, "./data/time_history/flux.th"),
    sink_head=os.path.join(bds_dir, "./data/channel_depletion/vsink_dated.th"),
    source_head=os.path.join(bds_dir, "./data/channel_depletion/vsource_dated.th"),
):
    """Calculate an estimate of Net Delta Outflow from boundary inputs applied to SCHISM"""

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

    flux_df = read_flux(
        flux=flux_file,
        flux_head=flux_head,
        time_basis=time_basis,
        elapsed_unit=elapsed_unit,
    )

    comb_dict = {
        "Northern Flow": [
            "sac",
            "american",
            "yolo_toedrain",
            "yolo",
            "east",
            "calaveras",
            "northbay",
        ],
        "Exports": ["ccc_rock", "ccc_old", "ccc_victoria", "swp", "cvp"],
        "Sac at Freeport": ["sac", "american"],
    }

    comb_df = combine_flux(
        flux_df,
        comb_dict,
        time_basis=time_basis,
        elapsed_unit=elapsed_unit,
        flux_head=flux_head,
    )

    dcu_df, src, sink = calc_net_source_sink(
        vsource_file=vsource_file,
        vsink_file=vsink_file,
        time_basis=time_basis,
        elapsed_unit=elapsed_unit,
        vsource_head=source_head,
        vsink_head=sink_head,
        search_term="delta",
    )

    # Resample to 15 min
    dcu_df = dcu_df.resample("15min").ffill()

    ndoi_df = dcu_df + comb_df["Exports"] + comb_df["Northern Flow"] + flux_df["sjr"]
    ndoi_df.name = "Boundary Input NDOI"
    ndoi_df.index.name = "datetime"
    ndoi_df = ndoi_df.dropna()

    return ndoi_df


@click.command(
    help="Command line function for calculating NDOI based on SCHISM boundary inputs"
)
@click.option("--flux-file", default="flux.th", help="Flux file path")
@click.option("--vsource-file", default="vsource.th", help="Vsource file path")
@click.option("--vsink-file", default="vsink.th", help="Vsink file path")
@click.option(
    "--time-basis",
    default=None,
    help="Time basis (start date, e.g. '2016-04-27') if none is provided, it will be inferred from param.nml",
)
@click.option("--elapsed-unit", default="s", help="Elapsed unit ('s' or 'd')")
@click.option("--output", default=None, help="Optional output CSV file")
@click.help_option("--help", "-h")
def calc_indoi_cli(
    flux_file, vsource_file, vsink_file, time_basis, elapsed_unit, output
):
    """CLI for calculating Net Delta Outflow Index (NDOI)"""
    ndoi_df = calc_indoi(
        flux_file=flux_file,
        vsource_file=vsource_file,
        vsink_file=vsink_file,
        time_basis=time_basis,
        elapsed_unit=elapsed_unit,
    )
    if output:
        ndoi_df.to_csv(output)
        print(f"Saved NDOI to {output}")
    else:
        print(ndoi_df)


if __name__ == "__main__":
    calc_indoi_cli()
