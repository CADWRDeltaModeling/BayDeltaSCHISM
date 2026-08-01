#!/usr/bin/env python
"""Convert processed structure gate products to SCHISM ``.th`` input files.

Supported ``--structure`` choices:

- ``ccfb_radial``: CCFB radial gate product (ndup/height in feet) from
    ``structures_processed``.
- ``smscg_radial_ops``: SMSCG radial gate operation coefficients from
    ``structures_processed`` ops log.
- ``smscg_radial_heights``: SMSCG radial heights derived from Wonderware gate
    position data in ``structures_formatted``.
- ``smscg_flash``: SMSCG flashboards coefficients from ops log.
- ``smscg_boat_lock``: SMSCG boat lock coefficients from ops log using the
    inverse status mapping of ``smscg_flash``.
"""

import logging
from io import StringIO
from pathlib import Path

import click
import numpy as np
import pandas as pd
import vtools.functions.unit_conversions as units

from dms_datastore import read_ts_repo

logger = logging.getLogger(__name__)


STRUCTURE_MAP = {
    "ccfb_radial": {
        "station_id": "ccfb",
        "variable": "height",
        "subloc": "radial",
        "repo": "structures_processed",
    }
}

STRUCTURE_CHOICES = [
    "ccfb_radial",
    "smscg_radial_ops",
    "smscg_radial_heights",
    "smscg_flash",
    "smscg_boat_lock",
]

SMSCG_RADIAL_CONST = {"install": 1, "elev": -6.86, "width": 10.97, "height": 10.00}
SMSCG_FLASH_CONST = {"install": 1, "ndup": 1, "elev": -5.34, "width": 20.73}
SMSCG_BOAT_CONST = {"install": 1, "ndup": 1, "elev": -2.29, "width": 6.10}


def _normalize_index(df):
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()
    out = out.loc[~out.index.duplicated(keep="last")]
    out.index.name = "datetime"
    return out


def _build_ops_inline_comment_map(ops):
    """Build timestamp-indexed inline comment text from ops text fields."""
    # Prefer the most narrative field first to minimize clutter in VCS diffs.
    text_priority = ["remarks", "user_remarks", "action"]
    available = [c for c in text_priority if c in ops.columns]
    if not available:
        return {}

    out = {}
    last_msg = None
    for ts, row in ops[available].iterrows():
        msg = None
        for col in available:
            val = row[col]
            if pd.isna(val):
                continue
            sval = str(val).strip()
            if sval:
                msg = sval
                break

        if not msg:
            continue
        if msg == last_msg:
            continue

        out[pd.Timestamp(ts)] = msg
        last_msg = msg

    return out


def _write_th(df, fname, columns, float_format="%.2f", inline_comments=None):
    out = df.copy()
    out.index.name = "datetime"
    inline_comments = inline_comments or {}

    buf = StringIO()
    out[columns].to_csv(
        buf,
        sep=" ",
        float_format=float_format,
        date_format="%Y-%m-%dT%H:%M",
    )

    lines = buf.getvalue().splitlines()
    if not lines:
        return

    with open(fname, "w", encoding="utf-8", newline="\n") as f:
        # Header line (column names) always remains plain.
        f.write(lines[0] + "\n")
        row_lines = lines[1:]

        for ts, row_line in zip(out.index, row_lines):
            ts_key = pd.Timestamp(ts)
            msg = inline_comments.get(ts_key)
            if msg:
                f.write(f"{row_line} # {msg}\n")
            else:
                f.write(row_line + "\n")


def _read_smscg_ops(start=None, end=None):
    ops = read_ts_repo(
        "smscg",
        "ops",
        repo="structures_processed",
        dtypes="infer",
        force_regular=False,
        start=start,
        end=end,
    )
    return _normalize_index(ops)


def _read_smscg_heights(start=None, end=None):
    heights = read_ts_repo(
        "smscg",
        "height",
        subloc="radial",
        repo="structures_formatted",
        dtypes="infer",
        force_regular=False,
        start=start,
        end=end,
    )
    return _normalize_index(heights)


def _build_smscg_radial_ops_th(ops):
    gate_cols = ["gate_1", "gate_2", "gate_3"]
    missing = [c for c in gate_cols if c not in ops.columns]
    if missing:
        raise ValueError(f"SMSCG ops data missing required columns: {missing}")

    gates = ops[gate_cols].copy()
    for c in gate_cols:
        gates[c] = gates[c].astype("string").str.strip().str.lower()

    open_or_tidal = gates.isin({"open", "tidal"})
    open_only = gates.eq("open")

    ndup = open_or_tidal.sum(axis=1).astype(int)
    n_open = open_only.sum(axis=1).astype(int)

    out = pd.DataFrame(index=ops.index)
    out["install"] = SMSCG_RADIAL_CONST["install"]
    out["ndup"] = ndup
    out["op_down"] = ndup.gt(0).astype(float)
    out["op_up"] = np.where(ndup > 0, n_open / ndup, 0.0)
    out["elev"] = SMSCG_RADIAL_CONST["elev"]
    out["width"] = SMSCG_RADIAL_CONST["width"]
    out["height"] = SMSCG_RADIAL_CONST["height"]
    return out


def _build_smscg_flash_or_boatlock_th(ops, const, inverse=False):
    if "flashboards" not in ops.columns:
        raise ValueError("SMSCG ops data missing required column: flashboards")

    fb = ops["flashboards"].astype("string").str.strip().str.lower()
    is_in = fb.isin({"in", "installed", "closed", "up"})
    flash_coeff = np.where(is_in, 0.0, 1.0)
    coeff = 1.0 - flash_coeff if inverse else flash_coeff

    out = pd.DataFrame(index=ops.index)
    out["install"] = const["install"]
    out["ndup"] = const["ndup"]
    out["op_down"] = coeff
    out["op_up"] = coeff
    out["elev"] = const["elev"]
    out["width"] = const["width"]
    return out


def _keep_first_and_op_changes(df, op_cols=("op_down", "op_up")):
    """Keep first row and any row where operation coefficients change."""
    if df.empty:
        return df

    changed = df.loc[:, list(op_cols)].ne(df.loc[:, list(op_cols)].shift()).any(axis=1)
    changed.iloc[0] = True
    return df.loc[changed]


def _soften_gate_transitions(df):
    out = df[["ndup", "height"]].copy()
    out = out.reset_index().rename(columns={"index": "datetime"})
    out["datetime"] = pd.to_datetime(out["datetime"])
    out = out.sort_values("datetime").reset_index(drop=True)

    h = out["height"].fillna(0.0).round(2)
    h_prev = h.shift(1)

    is_opening = h_prev.le(0.0) & h.gt(1.0)
    is_closing = h_prev.gt(1.0) & h.le(0.0)

    injected = []

    for idx in is_opening[is_opening].index:
        t = out.at[idx, "datetime"]
        ndup_val = int(out.at[idx, "ndup"]) if pd.notna(out.at[idx, "ndup"]) else 1
        injected.append({"datetime": t - pd.Timedelta(minutes=2), "ndup": ndup_val, "height": 1.0})

    for idx in is_closing[is_closing].index:
        t_prev = out.at[idx - 1, "datetime"]
        ndup_val = int(out.at[idx - 1, "ndup"]) if pd.notna(out.at[idx - 1, "ndup"]) else 1
        injected.append({"datetime": t_prev + pd.Timedelta(minutes=2), "ndup": ndup_val, "height": 1.0})

    if injected:
        out = pd.concat([out, pd.DataFrame(injected)], ignore_index=True)
        out = out.sort_values("datetime")
        out = out.drop_duplicates(subset=["datetime"], keep="last").reset_index(drop=True)

    out["ndup"] = out["ndup"].fillna(0).round().astype(int)

    h_rounded = out["height"].round(2)
    mask_changed = h_rounded.ne(h_rounded.shift())
    out = out.loc[mask_changed].reset_index(drop=True)
    out["height"] = h_rounded.loc[mask_changed].reset_index(drop=True)

    out = out.set_index("datetime")
    out.index.name = "datetime"
    return out


def _build_smscg_radial_heights_th(heights):
    gate_cols = ["gate_1", "gate_2", "gate_3"]
    missing = [c for c in gate_cols if c not in heights.columns]
    if missing:
        raise ValueError(f"SMSCG height data missing required columns: {missing}")

    gates = heights[gate_cols].astype(float)
    mask = gates > 0.16
    ndup = mask.sum(axis=1)
    sum_heights = gates.where(mask).sum(axis=1)
    height_ft = np.where(ndup > 0, sum_heights / ndup, 0.0)

    summary = pd.DataFrame(index=heights.index)
    summary["ndup"] = ndup.astype(int)
    summary["height"] = pd.Series(height_ft, index=heights.index) * units.FT2M

    smoothed = _soften_gate_transitions(summary)

    out = pd.DataFrame(index=smoothed.index)
    out["install"] = SMSCG_RADIAL_CONST["install"]
    out["ndup"] = smoothed["ndup"].astype(int)
    out["op_down"] = 1.0
    out["op_up"] = 1.0
    out["elev"] = SMSCG_RADIAL_CONST["elev"]
    out["width"] = SMSCG_RADIAL_CONST["width"]
    out["height"] = smoothed["height"]
    return out


def write_ccf_th(fname, df):
    """Write an ndup/height frame (height in feet) to a SCHISM *.th file."""
    df = df.copy()
    df.index.name = "datetime"
    df["height"] = df["height"] * units.FT2M
    df["elev"] = "-4.0244"
    df["width"] = "6.096"
    df["op_down"] = "1.0"
    df["op_up"] = "0.0"
    df["ndup"] = df.ndup.astype(int)
    df["install"] = int(1)
    df[["install", "ndup", "op_down", "op_up", "elev", "width", "height"]].to_csv(
        fname, sep=" ", float_format="%.2f", date_format="%Y-%m-%dT%H:%M"
    )


def convert_struct_data_schism(
    structure,
    output,
    start=None,
    end=None,
):
    """Convert one structure's processed gate product to SCHISM ``.th`` format."""
    output_path = Path(output)
    logger.info("Converting structure=%s to %s", structure, output_path)

    def _raise_if_empty(df, source_label):
        if df is None or df.empty:
            raise ValueError(
                "No data found for requested window"
                f" (source={source_label}, start={start}, end={end}). "
                "Try omitting --start/--end for sparse, event-based structure logs."
            )

    if structure == "ccfb_radial":
        spec = STRUCTURE_MAP[structure]
        height_ts = read_ts_repo(
            spec["station_id"],
            spec["variable"],
            subloc=spec["subloc"],
            repo=spec["repo"],
            force_regular=False,
            start=start,
            end=end,
        )
        _raise_if_empty(height_ts, "ccfb_radial")
        logger.info("Last timestamp in source data: %s", height_ts.last_valid_index())
        write_ccf_th(output_path, height_ts)
        return

    if structure == "smscg_radial_ops":
        ops = _read_smscg_ops(start=start, end=end)
        _raise_if_empty(ops, "smscg_ops")
        out = _build_smscg_radial_ops_th(ops)
        _write_th(
            out,
            output_path,
            ["install", "ndup", "op_down", "op_up", "elev", "width", "height"],
            inline_comments=_build_ops_inline_comment_map(ops),
        )
        return

    if structure == "smscg_flash":
        ops = _read_smscg_ops(start=start, end=end)
        _raise_if_empty(ops, "smscg_ops")
        out = _build_smscg_flash_or_boatlock_th(ops, const=SMSCG_FLASH_CONST, inverse=False)
        out = _keep_first_and_op_changes(out)
        _write_th(
            out,
            output_path,
            ["install", "ndup", "op_down", "op_up", "elev", "width"],
            inline_comments=_build_ops_inline_comment_map(ops),
        )
        return

    if structure == "smscg_boat_lock":
        ops = _read_smscg_ops(start=start, end=end)
        _raise_if_empty(ops, "smscg_ops")
        out = _build_smscg_flash_or_boatlock_th(ops, const=SMSCG_BOAT_CONST, inverse=True)
        out = _keep_first_and_op_changes(out)
        _write_th(
            out,
            output_path,
            ["install", "ndup", "op_down", "op_up", "elev", "width"],
            inline_comments=_build_ops_inline_comment_map(ops),
        )
        return

    if structure == "smscg_radial_heights":
        heights = _read_smscg_heights(start=start, end=end)
        _raise_if_empty(heights, "smscg_radial_heights")
        out = _build_smscg_radial_heights_th(heights)
        _write_th(out, output_path, ["install", "ndup", "op_down", "op_up", "elev", "width", "height"], float_format="%.2f")
        return

    raise ValueError(f"Unsupported structure value: {structure}")


@click.command("convert_struct_data_schism")
@click.option(
    "--structure",
    type=click.Choice(STRUCTURE_CHOICES, case_sensitive=False),
    required=True,
    help=(
        "Structure key to convert. Choices: "
        "ccfb_radial, smscg_radial_ops, smscg_radial_heights, "
        "smscg_flash, smscg_boat_lock."
    ),
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to output SCHISM .th file.",
)
@click.option(
    "--start",
    default=None,
    help="Optional inclusive start datetime.",
)
@click.option(
    "--end",
    default=None,
    help="Optional inclusive end datetime.",
)
@click.option(
    "--logdir",
    default=None,
    type=click.Path(),
    help="Directory for log files.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.help_option("-h", "--help")
def convert_struct_data_schism_cli(structure, output, start, end, logdir, debug):
    """Convert processed structure gate series to SCHISM ``.th`` format.

        Notes:
        - For ops-log based structures (``smscg_radial_ops``, ``smscg_flash``,
            ``smscg_boat_lock``), text fields such as ``action``, ``remarks``, and
            ``user_remarks`` are preserved as inline ``#`` comments on matching
            timestamp rows in the output.
        - If a selected ``--start/--end`` window has no records, the command
            raises a ``ValueError`` with guidance to omit the window for sparse,
            event-based logs.

    Examples:
        convert_struct_data_schism --structure ccfb_radial --output ccfb_radial.th
        convert_struct_data_schism --structure smscg_radial_ops --output smscg_radial.th
        convert_struct_data_schism --structure smscg_radial_heights --output smscg_radial_heights.th
        convert_struct_data_schism --structure smscg_flash --output smscg_flash.th
        convert_struct_data_schism --structure smscg_boat_lock --output smscg_boatlock.th
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
        logfile_prefix="convert_struct_data_schism",
    )

    start_ts = pd.to_datetime(start) if start else None
    end_ts = pd.to_datetime(end) if end else None

    convert_struct_data_schism(
        structure=structure.lower(),
        output=output,
        start=start_ts,
        end=end_ts,
    )


if __name__ == "__main__":
    convert_struct_data_schism_cli()
