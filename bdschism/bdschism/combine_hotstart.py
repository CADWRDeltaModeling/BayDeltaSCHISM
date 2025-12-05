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

    Parameters
    ----------
    run_dir : str
        SCHISM run directory (where param.nml typically lives).
    outputs_dir : str
        Directory containing parallel hotstart_000000_*.nc files. If relative,
        it is interpreted relative to run_dir.
    out_dir : str or None
        Archive directory. If relative, it is interpreted relative to run_dir.

    Returns
    -------
    run_dir_abs, outputs_dir_abs, out_dir_abs : tuple[str, str, Optional[str]]
        Absolute paths.
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

    Parameters
    ----------
    config_log : bool, optional
        If True, log configuration source via get_settings.

    Returns
    -------
    str
        Name (or full path) of the combine_hotstart executable.

    Raises
    ------
    RuntimeError
        If combine_hotstart is not defined in settings, or is not on PATH.
    """
    import shutil as _shutil

    settings = config.get_settings(config_log=config_log)

    # Dynaconf returns attributes; we expect "combine_hotstart" key in config.
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

    Parameters
    ----------
    outputs_dir_abs : str
        Absolute path to outputs directory containing hotstart_000000_*.nc.

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by datetime with a single column 'iteration'.

    Raises
    ------
    RuntimeError
        If no hotstarts are found or inventory cannot be constructed.
    """
    if not os.path.isdir(outputs_dir_abs):
        raise RuntimeError(f"Outputs directory does not exist: {outputs_dir_abs}")

    df = hotstart_inventory(
        run_start=None,
        dt=None,
        nday=None,
        workdir=outputs_dir_abs,
        paramfile=None,
        hot_freq=None,
        expected=False,
    )
    if df is None or df.empty:
        raise RuntimeError(
            f"No hotstarts found in outputs directory: {outputs_dir_abs}"
        )

    # Ensure sorted by datetime
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

    Parameters
    ----------
    df : pandas.DataFrame
        Hotstart inventory with DatetimeIndex and column 'iteration'.
    latest : bool, optional
        If True, select the most recent hotstart.
    before : str or pandas.Timestamp, optional
        If given, select the last hotstart with datetime on or before this date.
        Date string is interpreted by pandas.to_datetime.
    iteration : int, optional
        If given, select the row with this iteration.
    every : int, optional
        If given, select every Nth hotstart in time order (10 -> 10th, 20th, ...).

    Returns
    -------
    list of (iteration, datetime)
        List of pairs representing the desired hotstarts.

    Raises
    ------
    ValueError
        If no matching hotstarts are found, or parameters are inconsistent.
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

    df = df.copy()
    df = df.sort_index()

    if latest:
        # Most recent hotstart
        it = int(df["iteration"].iloc[-1])
        t = df.index[-1]
        return [(it, t)]

    if before is not None:
        # "On or before" a calendar date
        before_ts = pd.to_datetime(before)
        mask = df.index <= before_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        df_sel = df[mask]
        if df_sel.empty:
            raise ValueError(
                f"No hotstarts found on or before {before_ts.date()} "
                f"(outputs start at {df.index[0]})."
            )
        it = int(df_sel["iteration"].iloc[-1])
        t = df_sel.index[-1]
        return [(it, t)]

    if iteration is not None:
        df_sel = df[df["iteration"] == int(iteration)]
        if df_sel.empty:
            raise ValueError(
                f"No hotstart with iteration={iteration} found in inventory."
            )
        # If multiple entries (shouldn't normally happen), take the last one
        it = int(iteration)
        t = df_sel.index[-1]
        return [(it, t)]

    # every
    if every is not None:
        if every <= 0:
            raise ValueError("--every must be a positive integer.")
        # Every Nth hotstart (10th, 20th, 30th, ...)
        pairs: List[tuple[int, pd.Timestamp]] = []
        for idx, (t, row) in enumerate(df.iterrows(), start=1):
            if idx % every == 0:
                pairs.append((int(row["iteration"]), t))
        if not pairs:
            raise ValueError(
                f"--every={every} selected no hotstarts "
                f"(inventory length={len(df)})."
            )
        return pairs

    # Should not reach here
    raise ValueError("Selection logic error: no mode matched.")


def _make_hotstart_name(
    dt: pd.Timestamp,
    iteration: int,
    prefix: str = "",
) -> str:
    """
    Construct the canonical hotstart filename.

    Pattern:
        hotstart[.PREFIX].YYYYMMDD.ITER.nc

    Parameters
    ----------
    dt : pandas.Timestamp
        Datetime associated with the hotstart.
    iteration : int
        Iteration number.
    prefix : str, optional
        Optional prefix to insert after 'hotstart.'.

    Returns
    -------
    str
        Filename (no directory).
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

    Parameters
    ----------
    exe : str
        Executable name (e.g., 'combine_hotstart7').
    iteration : int
        Iteration to combine.
    outputs_dir_abs : str
        Directory to use as cwd when running the executable.

    Returns
    -------
    str
        Absolute path to the combined file 'hotstart_it=ITER.nc'.

    Raises
    ------
    RuntimeError
        If the executable fails or the expected output file is missing.
    """
    cmd = [exe, "-i", str(iteration)]
    # Run in outputs dir so the exe finds the partitioned hotstart files.
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

    # Expect output file named hotstart_it=ITER.nc in outputs_dir_abs
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

    This function wraps the native combine_hotstart executable (configured via
    bdschism settings) and uses schimpy.hotstart_inventory to map between
    iterations and datetimes. It can:
      * select the latest hotstart,
      * select the last hotstart on or before a date,
      * select a specific iteration, or
      * archive every Nth hotstart.

    The combined files are renamed to:

        hotstart[.PREFIX].YYYYMMDD.ITER.nc

    and either:
      * placed in `run_dir` and linked to `hotstart.nc` (links=True),
      * placed in `out_dir` (out_dir != None, links=False), or
      * placed in `run_dir` (links=False, out_dir=None).

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
        If provided, select the last hotstart on or before this date.
    iteration : int, optional
        If provided, combine this specific iteration.
    every : int, optional
        If provided, archive every Nth hotstart in time order (10 -> 10th, 20th, ...).
    out_dir : str, optional
        Archive directory. If relative, interpreted relative to run_dir. Mutually
        exclusive with `links` if you want "links-only" semantics; if both are
        provided, a ValueError is raised.
    links : bool, optional
        If True, create a link named hotstart.nc in run_dir pointing to the most
        recently combined file. Uses bdschism.settings.create_link.
    config_log : bool, optional
        If True, log configuration source when loading settings.

    Returns
    -------
    list of str
        Absolute paths of the combined hotstart files that were created.

    Raises
    ------
    ValueError
        If selection flags are inconsistent or if both out_dir and links are
        used in an incompatible way.
    RuntimeError
        For configuration or execution failures.
    """
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

    exe = _get_settings_executable(config_log=config_log)
    inventory_df = _load_inventory(outputs_dir_abs)
    selections = _select_iteration_and_time(
        df=inventory_df,
        latest=latest,
        before=before,
        iteration=iteration,
        every=every,
    )

    created_files: List[str] = []

    # Ensure archive directory exists if specified
    if out_dir_abs is not None:
        os.makedirs(out_dir_abs, exist_ok=True)

    # For each selected (iteration, datetime), run the exe, rename, move, and
    # optionally create links.
    for it, dt in selections:
        # 1. Run native combine executable
        src = _run_combine_executable(exe=exe, iteration=it, outputs_dir_abs=outputs_dir_abs)

        # 2. Decide destination directory
        if out_dir_abs is not None and every is not None:
            # Archive mode for every-N hotstarts
            dest_dir = out_dir_abs
        elif out_dir_abs is not None and every is None and not links:
            # Archive single hotstart
            dest_dir = out_dir_abs
        else:
            # Default: place in run_dir
            dest_dir = run_dir_abs

        os.makedirs(dest_dir, exist_ok=True)

        # 3. Destination filename
        dest_basename = _make_hotstart_name(dt=dt, iteration=it, prefix=prefix)
        dest = os.path.join(dest_dir, dest_basename)

        if os.path.exists(dest):
            if not overwrite:
                raise RuntimeError(
                    f"Destination file already exists: {dest}\n"
                    f"Use --overwrite to replace it."
                )
            os.remove(dest)

        shutil.move(src, dest)

        created_files.append(os.path.abspath(dest))

    # 5. Links behavior
    # For links=True, always link to the *latest* combined file in run_dir_abs.
    if links:
        if not created_files:
            raise RuntimeError("No hotstart files were created to link.")
        # Choose the last created file as the target for hotstart.nc
        target = created_files[-1]
        link_path = os.path.join(run_dir_abs, "hotstart.nc")
        print(f"Creating link {link_path} -> {target}")
        config.create_link(target, link_path)

    return created_files


@click.command(
    help=(
        "Combine SCHISM parallel hotstart files using the configured "
        "combine_hotstart executable, and rename/optionally link them.\n\n"
        "Examples:\n"
        "  combine_hotstart --latest --links --prefix retro\n"
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
    "--config-log",
    is_flag=True,
    help="Log configuration source when loading bdschism settings.",
)

@click.option(
    "--overwrite",
    is_flag=True,
    help="Allow overwriting an existing destination hotstart file."
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
    config_log,
    overwrite
):
    """
    CLI wrapper for combine_hot.

    This function parses command-line options and delegates to combine_hot().
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
            overwrite=overwrite
        )
    except Exception as exc:
        # ClickException gives a non-zero exit with a readable message.
        raise click.ClickException(str(exc))

    if not created:
        click.echo("No hotstart files were created.")
    else:
        click.echo("Created hotstart files:")
        for path in created:
            click.echo(f"  {path}")


if __name__ == "__main__":
    combine_hotstart_cli()
