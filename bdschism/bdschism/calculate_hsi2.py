"""
"""

from pathlib import Path
import logging
import argparse
import numpy as np
import pandas as pd
import xarray as xr
import suxarray as sx

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


def create_argparser():
    argparser = argparse.ArgumentParser()
    # argparser.add_argument("--path_study", type=lambda s: Path(s))
    argparser.add_argument("--path_common", type=lambda s: Path(s))
    argparser.add_argument("--path_postprocess", default=".", type=lambda s: Path(s))
    # argparser.add_argument(
    #     "--date_base", type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d")
    # )
    # argparser.add_argument(
    #     "--date_start", type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d")
    # )
    # argparser.add_argument(
    #     "--date_end", type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d")
    # )
    return argparser


def main():
    argparser = create_argparser()
    args = argparser.parse_args()

    # path_study = Path(args.path_study)
    path_common = Path(args.path_common)
    path_postprocess = Path(args.path_postprocess)
    # date_base = args.date_base
    # year = date_base.year
    # date_start = args.date_start
    # date_end = args.date_end

    # day_start = (date_start - date_base).days + 1
    # day_end = (date_end - date_base).days + 1

    # sx_ds = read_out2d_and_create_grid(path_study, day_start, day_end)

    logging.info("Reading postprocessed depth-averaged data...")
    chunks = {"time": 48}
    path_depth_averaged_salinity_at_face = (
        path_postprocess / "depth_averaged_salinity_at_face.nc"
    )
    ds_depth_averaged_salinity_at_face = xr.open_dataset(
        path_depth_averaged_salinity_at_face, chunks=chunks
    )
    path_depth_averaged_horizontalVelX_at_face = (
        path_postprocess / "depth_averaged_horizontalVelX_at_face.nc"
    )
    ds_depth_averaged_horizontalVelX_at_face = xr.open_dataset(
        path_depth_averaged_horizontalVelX_at_face, chunks=chunks
    )
    path_depth_averaged_horizontalVelY_at_face = (
        path_postprocess / "depth_averaged_horizontalVelY_at_face.nc"
    )
    ds_depth_averaged_horizontalVelY_at_face = xr.open_dataset(
        path_depth_averaged_horizontalVelY_at_face, chunks=chunks
    )
    year = (
        ds_depth_averaged_salinity_at_face.time.values[0]
        .astype("datetime64[Y]")
        .astype(int)
        + 1970
    )

    logging.info("Read quantile data...")

    chunks = {"time": 48}
    path_temperature_quantile_at_face = path_common / "temperature_quantile_at_face.nc"
    ds_temperature_quantile_at_face = xr.open_dataset(
        path_temperature_quantile_at_face, chunks=chunks
    )
    da_temperature_quantile_at_face = (
        ds_temperature_quantile_at_face.temperature_quantile_at_face
    )
    n_periods = da_temperature_quantile_at_face.time.size
    # Replace with the actual year
    start_date_jul = pd.to_datetime(da_temperature_quantile_at_face.time.values[0])
    start_date = pd.to_datetime(f"{year}-{start_date_jul.month}-{start_date_jul.day}")
    timestamps = pd.date_range(start=start_date, freq="1D", periods=n_periods)
    da_temperature_quantile_at_face = da_temperature_quantile_at_face.assign_coords(
        time=timestamps
    )
    chunks = {"time": 48}
    path_turbidity_quantile_at_face = path_common / "turbidity_quantile_at_face.nc"
    ds_turbidity_quantile_at_face = xr.open_dataset(
        path_turbidity_quantile_at_face, chunks=chunks
    )
    da_turbidity_quantile_at_face = (
        ds_turbidity_quantile_at_face.turbidity_quantile_at_face
    )
    n_periods = da_turbidity_quantile_at_face.time.size
    start_date_jul = pd.to_datetime(da_temperature_quantile_at_face.time.values[0])
    start_date = pd.to_datetime(f"{year}-{start_date_jul.month}-{start_date_jul.day}")
    timestamps = pd.date_range(start=start_date, freq="1D", periods=n_periods)
    da_turbidity_quantile_at_face = da_turbidity_quantile_at_face.assign_coords(
        time=timestamps
    )

    da_daily_salinity_fraction_under_6_at_face = (
        xr.where(
            ds_depth_averaged_salinity_at_face.depth_averaged_salinity_at_face < 6.0,
            1,
            0,
        )
        .resample(time="1D", origin="start")
        .mean()
    )
    da_daily_salinity_fraction_under_6_at_face = shift_30min_up(
        da_daily_salinity_fraction_under_6_at_face
    )
    da_turbidity_levels = xr.where(da_turbidity_quantile_at_face > 12.0, 1, 0).sum(
        dim="quantile"
    )

    da_probability = xr.apply_ufunc(
        interpolate_turbidity_cutoff_probability,
        da_turbidity_quantile_at_face,
        da_turbidity_levels,
        input_core_dims=[
            [
                "quantile",
            ],
            [],
        ],
        output_dtypes=float,
        dask="parallelized",
    )

    da_temperature_levels = xr.where(da_temperature_quantile_at_face < 24.0, 1, 0).sum(
        dim="quantile"
    )
    da_si_temperature = xr.apply_ufunc(
        lambda v: np.array([0, 0.25, 0.5, 0.75, 1.0])[v],
        da_temperature_levels,
        dask="parallelized",
    )
    da_depth_averaged_hvel_mag_at_face = xr.apply_ufunc(
        lambda v_x, v_y: np.hypot(v_x, v_y),
        ds_depth_averaged_horizontalVelX_at_face.depth_averaged_horizontalVelX_at_face,
        ds_depth_averaged_horizontalVelY_at_face.depth_averaged_horizontalVelY_at_face,
        dask="parallelized",
    )
    da_depth_averaged_hvel_mag_daily_max_at_face = (
        da_depth_averaged_hvel_mag_at_face.resample(time="1D", origin="start").max()
    )
    da_depth_averaged_hvel_mag_daily_max_at_face = shift_30min_up(
        da_depth_averaged_hvel_mag_daily_max_at_face
    )
    da_hsi = (
        0.67 * da_daily_salinity_fraction_under_6_at_face
        + 0.33 * da_depth_averaged_hvel_mag_daily_max_at_face
    )
    da_hsi_final = (1.0 - 0.6 * da_probability) * da_hsi * da_si_temperature
    da_hsi_final.name = "hsi"
    da_hsi_final.attrs["units"] = "dimensionless"
    da_hsi_final.attrs["long_name"] = "Habitat Suitability Index"
    path_hsi = path_postprocess / "hsi.nc"
    da_hsi_final.to_dataset().to_netcdf(path_hsi)
    logging.info("Done...")


def interpolate_turbidity_cutoff_probability(turb, levels):
    """Interpolate turbidity probability at 12 NTU from turbidity quantile data"""
    probability_all = np.zeros_like(turb)
    # The last dimension through apply_ufnuc is the quantile dimension
    funclist = [
        lambda v1, v2: (12.0 - v1) / (v2 - v1) * 0.20 + 0.05,
        lambda v1, v2: (12.0 - v1) / (v2 - v1) * 0.25 + 0.25,
        lambda v1, v2: (12.0 - v1) / (v2 - v1) * 0.25 + 0.5,
        lambda v1, v2: (12.0 - v2) / (v2 - v1) * 0.25 + 0.75,
    ]
    n_quantiles = turb.shape[-1]
    for l in range(n_quantiles):
        # For the last quantile, use the previous quantile set
        l_ = l if l != n_quantiles - 1 else l - 1
        v1 = turb[..., l_]
        v2 = turb[..., l_ + 1]
        probability_all[..., l] = funclist[l](v1, v2)
    result = np.select(
        [levels == i for i in range(n_quantiles)],
        [probability_all[..., i] for i in range(n_quantiles)],
        default=0.0,
    )
    np.clip(result, 0.0, 1.0, out=result)
    return result


def shift_30min_up(da):
    """Shift time coordinate 30 minutes up"""
    return da.assign_coords(time=da.coords["time"] - pd.to_timedelta("30m"))


if __name__ == "__main__":
    main()
