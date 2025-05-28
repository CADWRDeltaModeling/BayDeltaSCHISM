from schimpy.th_calcs import calc_net_source_sink, combine_flux, read_flux
import schimpy.param as parms
import pandas as pd
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

    if time_basis is None:
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

    dcu_df = calc_net_source_sink(
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
    ndoi_df.columns = ["Boundary Input NDOI"]
    ndoi_df = ndoi_df.dropna()

    return ndoi_df


if __name__ == "__main__":
    calc_indoi()
