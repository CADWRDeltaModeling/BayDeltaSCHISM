#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Set the nudging links for a Bay-Delta SCHSIM model

2025-02-04: Customized
"""
import click

from datetime import datetime

import schimpy.param as parms
import bdschism.settings as config

import os

################# command line application #####################


def parse_var_map(ctx, param, value):
    """
    Parse a string of key=value pairs separated by commas into a dictionary.
    Expected format: "key1=value1,key2=value2"
    Used for var_map which feeds the gr3 formats for things like TEM=temperature
    """
    mapping = {}
    if value:  # Check if the value is not empty
        # Remove any surrounding quotes or spaces and split by comma
        pairs = value.split(",")
        for pair in pairs:
            print(pair)
            if "=" not in pair:
                raise click.BadParameter(
                    f"Invalid format for var_map: '{pair}'. Expected format key=value."
                )
            key, value = pair.split("=", 1)
            mapping[key.strip()] = value.strip()
    return mapping


def get_nudge_list(fname):

    params = parms.read_params(fname)
    if params["ibc"] !=0:
        raise ValueError(
            f"Barotropic model detected in {fname}- Nudging not applicable."
        )
    nc_nudge_list = []
    nc_dict = {
        1: "TEM",
        2: "SAL",
        3: "GEN",
        4: "AGE",
        5: "SED",
        6: "ECO",
        7: "ICM",
        8: "COS",
        9: "FIB",
        10: "TIMOR-NOT-ACTIVE",
        11: "FBM",
    }

    for i in range(1, 12):
        if params._namelist["OPT"][f"inu_tr({i})"]["value"] == 2:
            nc_nudge_list.append(nc_dict[i])

    return nc_nudge_list


def set_nudging(suffix: str, workdir=".", var_map={}, param_fn="param.nml"):
    """This is a utility to set up nudging files based on a naming convention common for BayDeltaSCHISM.
    Assumed this is on Linux or admin-priveleged Windows machine.

    Arguments
    ---------

    suffix: str
        This is the suffix used when preparing the nudging/gr files. For instance "obshycom" in SAL_nu_obshycom.nc
    workdir : str
        Directory where the links and changes are made
    var_map: str
        Unexpected mapping in key=value pairs, separated by commas. Ex: --var_map 'TEM=temperature,SAL=salinity'
    param_fn: str
        Which param.nml file will be used to determine module list. Should be the baroclinic param file. Default is `param.nml`

    """

    fname = os.path.join(workdir, param_fn)
    nc_nudge_list = get_nudge_list(fname)
    check_files = []
    gr3_color = "\033[36m"  # Light blue for gr3
    nc_color = "\033[34m"  # Dark blue for nc
    reset_color = "\033[0m"  # Reset color

    for MOD in nc_nudge_list:
        if MOD in var_map.keys():
            var_in_gr3 = var_map[MOD]
        else:
            var_in_gr3 = MOD

        var_gr3_in = "{var_in_gr3}_nudge_{suffix}.gr3".format(**locals())
        var_nc_in = "{MOD}_nu_{suffix}.nc".format(**locals())
        check_files.extend([var_gr3_in, var_nc_in])

        var_gr3_out = "{MOD}_nudge.gr3".format(**locals())
        var_nc_out = "{MOD}_nu.nc".format(**locals())

        print(
            f"\t{gr3_color}{MOD} .gr3{reset_color}: Linked {var_gr3_out} to {var_gr3_in}"
        )
        config.create_link(var_gr3_in, os.path.join(workdir, var_gr3_out))
        print(f"\t{nc_color}{MOD} .nc{reset_color}: Linked {var_nc_out} to {var_nc_in}")
        config.create_link(var_nc_in, os.path.join(workdir, var_nc_out))

    invalid_files = [
        cf for cf in check_files if not os.path.exists(os.path.join(workdir, cf))
    ]

    if invalid_files:
        red_color = "\033[91m"  # Red for main message
        pink_color = "\033[95m"  # Pink for filenames

        error_message = (
            f"{red_color}The following files are not in the directory:\n"
            + "\n".join(
                f"\t{pink_color}- {file}{reset_color}" for file in invalid_files
            )
        )

        raise ValueError(error_message)


@click.command(
    help=(
        "Command for setting the nudging module files for SCHISM. "
        "This command forwards arguments to the `set_nudging` function.\n\n"
        "Arguments:\n"
        "  SUFFIX  This is the suffix used when preparing the nudging/gr files. "
        "For instance 'obshycom' in SAL_nu_obshycom.nc"
    )
)
@click.argument("suffix", required=False)
@click.option(
    "--workdir", default=".", show_default=True, help="Simulation directory path."
)
@click.option(
    "--var_map",
    default="",
    callback=parse_var_map,
    help=(
        "Mapping in key=value pairs, separated by commas. "
        "Ex: --var_map 'TEM=temperature,SAL=salinity'"
    ),
)
@click.option(
    "--param",
    default="param.nml",
    help=(
        "Which param.nml file will be used to determine module list. "
        "Should be the baroclinic param file. Default is `param.nml`"
    ),
)
@click.option(
    "--config",
    "config_key",
    help=(
        "Name of a bdschism config key whose value should be used "
        "as the nudging suffix. Example: --config nudge_prefix"
    ),
)
@click.help_option("-h", "--help")
def set_nudging_cli(suffix, workdir, param, var_map, config_key):
    """Wrapper function for the `set_nudging` command."""
    from bdschism.settings import get_settings
    import os

    # Allow suffix to come from config if not given positionally
    if suffix is None and config_key:
        settings = get_settings()
        try:
            suffix = getattr(settings, config_key)
        except AttributeError as e:
            raise click.ClickException(
                f"Config key '{config_key}' not found in bdschism settings."
            ) from e
        click.echo(f"Using suffix '{suffix}' from config key '{config_key}'.")
    elif suffix is not None and config_key:
        # Explicit suffix overrides config; just be noisy about it
        settings = get_settings()
        cfg_val = getattr(settings, config_key, "<not found>")
        click.echo(
            f"Suffix '{suffix}' overrides --config {config_key} "
            f"(config value was {cfg_val!r})."
        )

    if suffix is None:
        raise click.ClickException(
            "You must supply either SUFFIX or --config CONFIG_KEY."
        )

    os.chdir(os.path.abspath(os.path.dirname(workdir)))
    set_nudging(suffix, workdir, var_map, param_fn=param)

if __name__ == "__main__":
    set_nudging_cli()
