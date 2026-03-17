import xarray as xr
import os
import click
import glob
import re
import numpy as np


def validate_time_step_consistency(time_values, atol=1e-9, max_report=20):
    """Validate constant time step and report exact mismatch locations."""

    times = np.asarray(time_values, dtype=float)
    if times.size < 2:
        print(
            "\tTime coordinate has fewer than 2 points; timestep consistency check skipped."
        )
        return

    dt = np.diff(times)
    expected_dt = dt[0]
    bad_idx = np.where(~np.isclose(dt, expected_dt, atol=atol, rtol=0.0))[0]

    if bad_idx.size == 0:
        print(f"\tTimestep is consistent: dt={expected_dt}.")
        return

    report_lines = [
        f"\tFound {bad_idx.size} inconsistent timestep(s). Expected dt={expected_dt}."
    ]
    for i in bad_idx[:max_report]:
        report_lines.append(
            f"  idx {i}->{i+1}: t0={times[i]}, t1={times[i+1]}, dt={dt[i]}"
        )
    if bad_idx.size > max_report:
        report_lines.append(f"  ... and {bad_idx.size - max_report} more mismatch(es).")

    raise ValueError("\n".join(report_lines))


def get_selected_files(template, start_num, end_num):
    """Get a sorted list of files matching the template and within the specified number range."""

    if "*" not in template:
        raise ValueError("template must include '*' wildcard, e.g., uv3d_*.th.nc")

    pattern = re.escape(template).replace(r"\*", r"(\d+)")
    matcher = re.compile(f"^{pattern}$")

    matched_files = glob.glob(template)
    selected = []
    for path in matched_files:
        match = matcher.match(path)
        if not match:
            continue
        num = int(match.group(1))
        if start_num <= num <= end_num:
            selected.append((num, path))

    selected.sort(key=lambda item: item[0])
    input_files = [path for _, path in selected]

    if not input_files:
        raise ValueError(
            f"No input files found for template '{template}' in range "
            f"[{start_num}, {end_num}]"
        )

    return input_files


def combine_nc(input_files, outfile):
    """Combines multiple NetCDF files (e.g., out2d_1.nc, out2d_2.nc, etc.) into a single NetCDF file along the time dimension."""

    # Load and combine the NetCDF files, dropping the first time slice
    # for every dataset except the first one to avoid duplicate boundaries.
    datasets = [xr.open_dataset(f, decode_times=False) for f in input_files]
    concat_datasets = []
    for idx, dataset in enumerate(datasets):
        if idx == 0:
            concat_datasets.append(dataset)
        else:
            concat_datasets.append(dataset.isel(time=slice(1, None)))

    combined_ds = xr.concat(concat_datasets, dim="time")

    # Update the time coordinate with the provided times
    validate_time_step_consistency(combined_ds["time"].values)

    # Save the combined dataset to a new NetCDF file
    out_dir = os.path.dirname(outfile)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    combined_ds.to_netcdf(outfile)

    for dataset in datasets:
        dataset.close()
    combined_ds.close()


def combine_uv3d(
    start_num,
    end_num,
    outfile,
    tmp_out_dir="./outputs.tropic/uv3d",
):

    template = f"{tmp_out_dir}/uv3d_*.th.nc"

    input_files = get_selected_files(template, start_num, end_num)

    combine_nc(input_files, outfile)
    
    print(f"\nOutfile written to : {outfile}")


def compare_dataarray_all_axes(validate_da, check_da, atol=1e-6, rtol=1e-6):
    """Check two DataArrays match on dims, coords, shape, and values."""

    if validate_da.dims != check_da.dims:
        raise ValueError(
            f"Dimension name/order mismatch: {validate_da.dims} != {check_da.dims}"
        )

    if validate_da.shape != check_da.shape:
        raise ValueError(f"Shape mismatch: {validate_da.shape} != {check_da.shape}")

    for dim in validate_da.dims:
        if dim in validate_da.coords and dim in check_da.coords:
            vcoord = validate_da.coords[dim].values
            ccoord = check_da.coords[dim].values
            if vcoord.shape != ccoord.shape:
                raise ValueError(
                    f"Coordinate shape mismatch on '{dim}': {vcoord.shape} != {ccoord.shape}"
                )
            if not np.allclose(vcoord, ccoord, atol=atol, rtol=rtol):
                bad_idx = np.where(~np.isclose(vcoord, ccoord, atol=atol, rtol=rtol))[0]
                i0 = int(bad_idx[0])
                raise ValueError(
                    f"Coordinate mismatch on '{dim}' at index {i0}: "
                    f"validate={vcoord[i0]}, check={ccoord[i0]}"
                )

    vvals = validate_da.values
    cvals = check_da.values
    same_values = np.allclose(vvals, cvals, atol=atol, rtol=rtol, equal_nan=True)
    if not same_values:
        bad_locs = np.argwhere(~np.isclose(vvals, cvals, atol=atol, rtol=rtol, equal_nan=True))
        first = tuple(int(i) for i in bad_locs[0])
        raise ValueError(
            f"Data mismatch at index {first}: "
            f"validate={vvals[first]}, check={cvals[first]}"
        )

    print("time_series matches across all axes and values.")


@click.command(
    help=(
        "Combine NetCDF files along the time dimension.\n\n"
        "\b\n"
        "Arguments:\n"
        "  TEMPLATE   Wildcard template for input files (must include '*').\n"
        "  START      First numeric index to include (inclusive).\n"
        "  END        Last numeric index to include (inclusive).\n\n"
        "\b\n"
        "Examples:\n"
        "  bds combine_nc './outputs.tropic/uv3d/uv3d_*.th.nc' 1 10 ./uv3d_combined.th.nc\n"
        "  bds combine_nc './outputs/out2d_*.nc' 1 5 ./out2d_combined.nc"
    )
)
@click.argument("template", type=str)
@click.argument(
    "start",
    type=int,
)
@click.argument(
    "end",
    type=int,
)
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default="./uv3D.th.nc",
    help="Output file path for the combined NetCDF (default: ./uv3D.th.nc).",
)
@click.option(
    "--tmp-out-dir",
    type=click.Path(),
    default=None,
    help=(
        "Directory containing uv3d intermediate files. "
        "Used only for uv3d mode; defaults to ./outputs.tropic/uv3d."
    ),
)
@click.help_option("-h", "--help")
def combine_nc_cli(template, start, end, output, tmp_out_dir):
    """Command line utility for combining NetCDF files.

    Example usage:
        bds combine_nc 'uv3d' 1 10 ./uv3d_combined.th.nc
    """

    if "uv3d" in template.lower():
        print("Combining uv3d files using combine_uv3d...")
        if tmp_out_dir is None:
            combine_uv3d(start, end, output)
        else:
            combine_uv3d(start, end, output, tmp_out_dir=tmp_out_dir)
    else:
        print(
            f"Combining generic NetCDF files using combine_nc and template: {template}..."
        )
        input_files = get_selected_files(template, start, end)
        combine_nc(input_files, output)


if __name__ == "__main__":
    combine_nc_cli()

    # os.chdir("/scratch/projects/dsp/updated_schism_202602/simulations/baseline_lhc_3")

    # start_num = 1
    # end_num = 3
    # outfile = "./uv3d_combined.th.nc"

    # combine_uv3d(start_num, end_num, outfile)

    # check_file = "./outputs.tropic/uv3D.th.nc"
    # check_ds = xr.open_dataset(check_file, decode_times=False)

    # validate_ds = xr.open_dataset(outfile, decode_times=False)

    # compare_dataarray_all_axes(validate_ds["time_series"], check_ds["time_series"])

    # check_ds.close()
    # validate_ds.close()
    