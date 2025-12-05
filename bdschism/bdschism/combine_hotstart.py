import os
import shutil
import subprocess
from typing import List, Optional, Union

import click
import pandas as pd

from schimpy.hotstart_inventory import hotstart_inventory
import bdschism.settings as config


def _resolve_paths(
    run_dir: str,
    outputs_dir: str,
    out_dir: Optional[str],
) -> tuple[str, str, Optional[str]]:
    """
    Resolve absolute paths for run_dir, outputs_dir, and out_dir.
    """
    run_dir_abs = os.path.abspath(run_dir)

    if os.path.isabs(outputs_dir):
        outputs_dir_abs = outputs_dir
    else:
        outputs_dir_abs = os.path.join(run_dir_abs, outputs_dir)

    out_dir_abs = None
    if out_dir is not None:
        if os.path.isabs(out_dir):
            out_dir_abs = out_dir
        else:
            out_dir_abs = os.path.join(run_dir_abs, out_dir)

    return run_dir_abs, outputs_dir_abs, out_dir_abs


def _get_settings_executable(config_log: bool = False) -> str:
    """
    Get the combine_hotstart executable name from bdschism settings and verify
    that it is on PATH.
    """
    import shutil as _shutil

    settings = config.get_settings(config_log=config_log)

    if not hasattr(settings, "combine_hotstart"):
        raise RuntimeError(
            "Configuration error: 'combine_hotstart' is not defined in bds_config.yaml."
        )

    exe = settings.combine_hotstart
    if not exe:
        raise RuntimeError(
            "Configuration error: settings.combine_hotstart is empty or undefined."
        )

    exe_on_path = _shutil.which(exe)
    if exe_on_path is None:
        raise RuntimeError(
            f"Executable '{exe}' (from settings.combine_hotstart) is not on PATH."
        )

    return exe


def _load_inventory(outputs_dir_abs: str) -> pd.DataFrame:
    """
    Load a hotstart inventory from the outputs directory.
    """
    if not os.path.isdir(outputs_dir_abs):
        raise RuntimeError(f"Outputs directory does not exist: {outputs_dir_abs}")

    # Let hotstart_inventory infer run_start, dt, nday, hot_freq from param.nml
    # in the run directory (CWD), while searching for hotstarts in outputs_dir_abs.
    df = hotstart_inventory(
        run_start=None,
        dt=None,
        nday=None,
        workdir=outputs_dir_abs,
        paramfile=None,
        hot_freq=None,
        expected=False,
    )
    print(df)
    if df is None or df.empty:
        raise RuntimeError(
            f"No hotstarts found in outputs directory: {outputs_dir_abs}"
        )

    df = df.sort_index()
    return df


def _select_iteration_and_time(
    df: pd.DataFrame,
    latest: bool = False,
    before: Optional[Union[str, pd.Timestamp]] = None,
    iteration: Optional[int] = None,
    every: Optional[int] = None,
) -> List[tuple[int, pd.Timestamp]]:
    """
    Given an inventory DataFrame, select one or more (iteration, datetime) pairs.
    """
    modes = sum(
        [
            bool(latest),
            before is not None,
            iteration is not None,
            every is not None,
        ]
    )
    if modes != 1:
        raise ValueError(
            "Exactly one of --latest, --before, --it/--iteration, or --every "
            "must be specified."
        )

    df = df.copy().sort_index()

    if latest:
        it = int(df["iteration"].iloc[-1])
        t = df.index[-1]
        print(f"Selected latest hotstart: iteration={it}, time={t}")
        return [(it, t)]

    if before is not None:
        before_ts = pd.to_datetime(before)
        # "On or before" the given calendar date
        mask = df.index <= before_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        df_sel = df[mask]
        if df_sel.empty:
            raise ValueError(
                f"No hotstarts found on or before {before_ts.date()} "
                f"(inventory starts at {df.index[0]})."
            )
        it = int(df_sel["iteration"].iloc[-1])
        t = df_sel.index[-1]
        print(f"Selected hotstart on/before {before_ts.date()}: iteration={it}, time={t}")
        return [(it, t)]

    if iteration is not None:
        df_sel = df[df["iteration"] == int(iteration)]
        if df_sel.empty:
            raise ValueError(
                f"No hotstart with iteration={iteration} found in inventory."
            )
        it = int(iteration)
        t = df_sel.index[-1]
        print(f"Selected hotstart by iteration: iteration={it}, time={t}")
        return [(it, t)]

    # every
    if every is not None:
        if every <= 0:
            raise ValueError("--every must be a positive integer.")
        pairs: List[tuple[int, pd.Timestamp]] = []
        for idx, (t, row) in enumerate(df.iterrows(), start=1):
            if idx % every == 0:
                it = int(row["iteration"])
                print(f"Selected hotstart #{idx} for --every={every}: iteration={it}, time={t}")
                pairs.append((it, t))
        if not pairs:
            raise ValueError(
                f"--every={every} selected no hotstarts "
                f"(inventory length={len(df)})."
            )
        return pairs

    raise ValueError("Selection logic error: no mode matched.")


def _make_hotstart_name(
    dt: pd.Timestamp,
    iteration: int,
    prefix: str = "",
) -> str:
    """
    Construct the canonical hotstart filename:

        hotstart[.PREFIX].YYYYMMDD.ITER.nc
    """
    datestr = dt.strftime("%Y%m%d")
    if prefix:
        return f"hotstart.{prefix}.{datestr}.{iteration}.nc"
    else:
        return f"hotstart.{datestr}.{iteration}.nc"


def _run_combine_executable(
    exe: str,
    iteration: int,
    outputs_dir_abs: str,
) -> str:
    """
    Run the native combine_hotstart executable for a single iteration.

    Returns absolute path to 'hotstart_it=ITER.nc'.
    """
    cmd = [exe, "-i", str(iteration)]
    print(f"Running {exe} in {outputs_dir_abs} with iteration {iteration}")
    result = subprocess.run(
        cmd,
        cwd=outputs_dir_abs,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Error running {exe} with iteration {iteration}.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    basename = f"hotstart_it={iteration}.nc"
    src = os.path.join(outputs_dir_abs, basename)
    if not os.path.exists(src):
        raise RuntimeError(
            f"Expected output file not found after running {exe}: {src}"
        )

    return src

def combine_hot(
    run_dir: str = ".",
    outputs_dir: str = "outputs",
    prefix: str = "",
    latest: bool = False,
    before: Optional[Union[str, pd.Timestamp]] = None,
    iteration: Optional[int] = None,
    every: Optional[int] = None,
    out_dir: Optional[str] = None,
    links: bool = False,
    config_log: bool = False,
    overwrite: bool = False,
) -> List[str]:
    """
    High-level API to combine SCHISM hotstart files.

    This wraps the native combine_hotstart executable (configured via
    bdschism settings) and schimpy.hotstart_inventory to map between
    iterations and datetimes.

    Parameters
    ----------
    run_dir : str, optional
        SCHISM run directory. Defaults to current directory.
    outputs_dir : str, optional
        Directory containing parallel hotstart_000000_*.nc files. Default 'outputs'.
        If relative, interpreted relative to run_dir.
    prefix : str, optional
        Optional prefix inserted after 'hotstart.' in the output filename.
    latest : bool, optional
        If True, select the most recent hotstart.
    before : str or pandas.Timestamp, optional
        Select the last hotstart on or before this date.
    iteration : int, optional
        Combine this specific iteration.
    every : int, optional
        Archive every Nth hotstart in time order (10 -> 10th, 20th, ...).
    out_dir : str, optional
        Archive directory. If relative, interpreted relative to run_dir.
    links : bool, optional
        If True, create hotstart.nc in run_dir pointing to the most
        recently created file using bdschism.settings.create_link.
    config_log : bool, optional
        If True, log configuration source when loading settings.
    overwrite : bool, optional
        If True, allow overwriting an existing destination file.

    Returns
    -------
    list of str
        Absolute paths of the combined hotstart files that were created.
    """
    # Guard against the most confusing combo
    if links and every is not None and out_dir is not None:
        raise ValueError(
            "Using --every with both --links and --out-dir is ambiguous. "
            "Please choose either links-only (no out_dir) or archive-only "
            "(out_dir without links)."
        )

    run_dir_abs, outputs_dir_abs, out_dir_abs = _resolve_paths(
        run_dir=run_dir,
        outputs_dir=outputs_dir,
        out_dir=out_dir,
    )

    print(f"Run directory:     {run_dir_abs}")
    print(f"Outputs directory: {outputs_dir_abs}")
    if out_dir_abs is not None:
        print(f"Archive directory: {out_dir_abs}")

    exe = _get_settings_executable(config_log=config_log)
    print(f"Using combine_hotstart executable: {exe}")

    inventory_df = _load_inventory(outputs_dir_abs)
    selections = _select_iteration_and_time(
        df=inventory_df,
        latest=latest,
        before=before,
        iteration=iteration,
        every=every,
    )

    created_files: List[str] = []

    if out_dir_abs is not None:
        os.makedirs(out_dir_abs, exist_ok=True)

    # === THIS IS THE LOOP WE’RE TALKING ABOUT ===
    for it, dt in selections:
        # 1. Decide destination directory BEFORE running the combine exe
        if out_dir_abs is not None and every is not None:
            dest_dir = out_dir_abs
        elif out_dir_abs is not None and every is None and not links:
            dest_dir = out_dir_abs
        else:
            dest_dir = run_dir_abs

        os.makedirs(dest_dir, exist_ok=True)

        # 2. Destination filename BEFORE running the combine exe
        dest_basename = _make_hotstart_name(dt=dt, iteration=it, prefix=prefix)
        dest = os.path.join(dest_dir, dest_basename)

        # 3. Pre-check for existing file so we can fail fast
        if os.path.exists(dest) and not overwrite:
            raise RuntimeError(
                f"Destination file already exists: {dest}\n"
                f"Use --overwrite to replace it."
            )

        # 4. Run native combine executable to produce hotstart_it=ITER.nc
        src = _run_combine_executable(
            exe=exe,
            iteration=it,
            outputs_dir_abs=outputs_dir_abs,
        )

        # 5. Handle overwrite only after successful combine
        if os.path.exists(dest):
            # Only possible if overwrite=True, because we already bailed above otherwise
            print(f"Overwriting existing file: {dest}")
            os.remove(dest)

        # 6. Move combined file to destination
        print(f"Moving combined file:\n  {src}\n-> {dest}")
        shutil.move(src, dest)

        created_files.append(os.path.abspath(dest))

    # 7. Links behavior
    if links:
        if not created_files:
            raise RuntimeError("No hotstart files were created to link.")
        target = created_files[-1]
        link_path = os.path.join(run_dir_abs, "hotstart.nc")
        print(f"Creating link {link_path} -> {target}")
        config.create_link(target, link_path)

    return created_files



@click.command(
    help=(
        "Combine SCHISM parallel hotstart files using the configured "
        "combine_hotstart executable, then rename / optionally link them.\n\n"
        "Examples:\n"
        "  combine_hotstart --latest --links --prefix clinic\n"
        "  combine_hotstart --before 2014-03-26 --prefix retro\n"
        "  combine_hotstart --it 14400 --out-dir hotstart_archive --prefix retro\n"
        "  combine_hotstart --every 10 --out-dir hotstart_archive --prefix retro\n"
    )
)
@click.option(
    "--run-dir",
    default=".",
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    help="SCHISM run directory (default: current directory).",
)
@click.option(
    "--outputs-dir",
    default="outputs",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Directory containing parallel hotstart_000000_*.nc (default: 'outputs').",
)
@click.option(
    "--prefix",
    default="",
    type=str,
    help="Optional prefix inserted after 'hotstart.' in output filenames.",
)
@click.option(
    "--latest",
    is_flag=True,
    help="Use the latest available hotstart in the inventory.",
)
@click.option(
    "--before",
    default=None,
    type=str,
    help="Use the last hotstart on or before this date (e.g., '2014-03-26').",
)
@click.option(
    "-i",
    "--it",
    "iteration",
    default=None,
    type=int,
    help="Use a specific iteration number.",
)
@click.option(
    "--every",
    default=None,
    type=int,
    help="Archive every Nth hotstart in time order (10 -> 10th, 20th, ...).",
)
@click.option(
    "--out-dir",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True),
    help=(
        "Archive directory for combined hotstarts. "
        "If relative, interpreted relative to run-dir. "
        "If not given, files go to run-dir."
    ),
)
@click.option(
    "--links",
    is_flag=True,
    help=(
        "Create 'hotstart.nc' in run-dir pointing to the most recently created "
        "hotstart using bdschism.settings.create_link."
    ),
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Allow overwriting an existing destination hotstart file.",
)
@click.option(
    "--config-log",
    is_flag=True,
    help="Log configuration source when loading bdschism settings.",
)
@click.help_option("-h", "--help")
def combine_hotstart_cli(
    run_dir,
    outputs_dir,
    prefix,
    latest,
    before,
    iteration,
    every,
    out_dir,
    links,
    overwrite,
    config_log,
):
    """
    CLI wrapper for combine_hot().
    """
    try:
        created = combine_hot(
            run_dir=run_dir,
            outputs_dir=outputs_dir,
            prefix=prefix,
            latest=latest,
            before=before,
            iteration=iteration,
            every=every,
            out_dir=out_dir,
            links=links,
            config_log=config_log,
            overwrite=overwrite,
        )
    except Exception as exc:
        raise click.ClickException(str(exc))

    if not created:
        click.echo("No hotstart files were created.")
    else:
        click.echo("Created hotstart files:")
        for path in created:
            click.echo(f"  {path}")


if __name__ == "__main__":
    combine_hotstart_cli()
