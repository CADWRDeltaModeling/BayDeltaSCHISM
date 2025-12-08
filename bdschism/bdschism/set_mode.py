import os
from pathlib import Path
from schimpy import param as sch_param

import click

from bdschism.settings import get_settings, create_link


def _iter_links(links, mode_name: str):
    """
    Yield (target, source) pairs from the 'links' spec for a mode.

    Supports either:
      links:
        param.nml: param.nml.tropic
        bctides.in: bctides.in.2d

    or:
      links:
        - param.nml: param.nml.tropic
        - bctides.in: bctides.in.2d
    """
    if isinstance(links, dict):
        for target, source in links.items():
            yield str(target), str(source)
    elif isinstance(links, (list, tuple)):
        for entry in links:
            if not isinstance(entry, dict):
                raise click.ClickException(
                    f"Mode '{mode_name}': each item in 'links' must be a mapping "
                    f"like '- target: source', got {type(entry)}"
                )
            if len(entry) != 1:
                raise click.ClickException(
                    f"Mode '{mode_name}': each 'links' mapping must have exactly "
                    f"one key:value pair, got {entry}"
                )
            (target, source), = entry.items()
            yield str(target), str(source)
    else:
        raise click.ClickException(
            f"Mode '{mode_name}': unsupported 'links' type {type(links)}"
        )

def _resolve_mode(settings, mode_name: str):
    """Return the mode config object by name from settings.modes.

    Assumes 'modes' is a mapping from mode_name -> mode_config, e.g.:

      modes:
        tropic:
          links: ...
        clinic:
          links: ...
    """
    modes = getattr(settings, "modes", None)
    if not modes:
        raise click.ClickException(
            "No 'modes' configured in settings (bds_config.yaml or overrides)."
        )

    # Dynaconf usually gives a mapping-like object that supports dict-style access.
    try:
        mode = modes[mode_name]
    except Exception:
        # Build list of available names for a helpful error.
        try:
            available = list(modes.keys())
        except Exception:
            available = []

        raise click.ClickException(
            f"Unknown mode '{mode_name}'. Available modes: {', '.join(available) or '(none)'}"
        )

    return mode

def _apply_mode_params(params_spec, rundir: Path, dry_run: bool, hard_fail: bool) -> bool:
    """
    Apply 'params' entries for a mode.

    Expected config shape:

      modes:
        clinic:
          links: ...
          params:
            - file: param.nml
              set:
                run_nday: 365
                ihot: 1

    Returns
    -------
    any_error : bool
        True if any warnings were emitted (missing param files) while hard_fail=False.
    """
    any_error = False

    if not isinstance(params_spec, (list, tuple)):
        raise click.ClickException(
            "'params' must be a list of mappings with 'file' and 'set' keys."
        )

    for entry in params_spec:
        if not isinstance(entry, dict):
            raise click.ClickException(
                f"Each item in 'params' must be a mapping, got {type(entry)}"
            )

        param_file = entry.get("file")
        changes = entry.get("set")

        if not param_file or not isinstance(changes, dict):
            raise click.ClickException(
                "Each 'params' entry must have 'file' and a 'set' mapping."
            )

        param_path = rundir / param_file

        if not param_path.exists():
            msg = f"Param file does not exist for params entry: {param_path}"
            if hard_fail:
                raise click.ClickException(msg)
            click.echo(f"WARNING: {msg}", err=True)
            any_error = True
            continue

        if dry_run:
            click.echo(f"[DRY-RUN] Would update parameters in {param_path}:")
            for name, value in changes.items():
                click.echo(f"    {name} = {value}")
            continue

        # Read, modify, write using schimpy.param
        try:
            params = sch_param.read_params(str(param_path))
        except Exception as e:
            raise click.ClickException(f"Failed to read {param_path}: {e}") from e

        for name, value in changes.items():
            try:
                params.set_by_name_or_alias(name, value)
            except Exception as e:
                raise click.ClickException(
                    f"Failed to set '{name}' in {param_path}: {e}"
                ) from e

        try:
            params.write(str(param_path))
        except Exception as e:
            raise click.ClickException(
                f"Failed to write updated params to {param_path}: {e}"
            ) from e

    return any_error


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("arg1", metavar="[rundir=PATH|MODE]")
@click.argument("arg2", required=False, metavar="[MODE]")
@click.option(
    "--rundir",
    "rundir_opt",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Run directory (overrides 'rundir=PATH' syntax). Defaults to current directory.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done, but do not create or modify any links.",
)
@click.option(
    "--hard-fail/--no-hard-fail",
    default=True,
    show_default=True,
    help=(
        "If enabled, missing sources or other problems cause a non-zero exit code. "
        "If disabled, problems are reported as warnings but the command exits successfully."
    ),
)
def main(arg1, arg2, rundir_opt, dry_run, hard_fail):
    """
    Set a SCHISM run directory into a named MODE by creating configured links.

    Usage examples:

      \b
      set_mode clinic
      set_mode rundir=/path/to/run tropic
      set_mode --rundir /path/to/run tropic
    """
    # Resolve run directory and mode name from arguments/options.
    if rundir_opt is not None:
        # --rundir provided: treat ARG1 as mode, do not allow ARG2.
        if arg2 is not None:
            raise click.ClickException(
                "When using --rundir, provide exactly one positional argument (the MODE). "
                "Example: set_mode --rundir /path/to/run tropic"
            )
        rundir = rundir_opt
        mode_name = arg1
    else:
        # No --rundir: use positional syntaxes.
        if arg2 is None:
            # set_mode MODE
            rundir = Path(".")
            mode_name = arg1
        else:
            # set_mode rundir=/path/to/run MODE
            if not arg1.startswith("rundir="):
                raise click.ClickException(
                    "When two positional arguments are given, the first must be of the form "
                    "'rundir=PATH'. Example: set_mode rundir=/path/to/run tropic"
                )
            _, path_str = arg1.split("=", 1)
            rundir = Path(path_str)
            mode_name = arg2

    # Validate run directory.
    if not rundir.exists() or not rundir.is_dir():
        msg = f"Run directory does not exist or is not a directory: {rundir}"
        if hard_fail:
            raise click.ClickException(msg)
        click.echo(f"WARNING: {msg}", err=True)
        return

    # Load settings and resolve mode.
    settings = get_settings()
    mode = _resolve_mode(settings, mode_name)

    # links is optional — use .get to avoid BoxKeyError on Dynaconf Box
    links = mode.get("links") if isinstance(mode, dict) else getattr(mode, "links", None)

    # If no links are defined, treat as empty and continue
    if links is None:
        links = {}
    
    click.echo(f"Setting mode '{mode_name}' in run directory: {rundir}")

    any_error = False

    for target_rel, source_rel in _iter_links(links, mode_name):
        source = rundir / source_rel
        target = rundir / target_rel

        # Check that source exists.
        if not source.exists():
            msg = f"Source file does not exist for mode '{mode_name}': {source}"
            if hard_fail:
                raise click.ClickException(msg)
            click.echo(f"WARNING: {msg}", err=True)
            any_error = True
            continue

        # If target exists and is not a symlink, refuse to clobber.
        if target.exists() and not os.path.islink(target):
            msg = (
                f"Target path exists and is not a symlink: {target}. "
                "Refusing to overwrite."
            )
            if hard_fail:
                raise click.ClickException(msg)
            click.echo(f"WARNING: {msg}", err=True)
            any_error = True
            continue

        if dry_run:
            click.echo(f"[DRY-RUN] Would link {target} -> {source}")
        else:
            click.echo(f"Linking {target} -> {source}")
            create_link(str(source), str(target))

    # After links, optionally apply param changes if configured.
    params_spec = None
    if isinstance(mode, dict):
        params_spec = mode.get("params")
    else:
        params_spec = getattr(mode, "params", None)

    if params_spec:
        params_error = _apply_mode_params(params_spec, rundir, dry_run, hard_fail)
        any_error = any_error or params_error

    # If we had warnings but not hard failures, still exit 0.
    if any_error and not hard_fail:
        click.echo(
            "Completed with warnings (see above). "
            "Use --hard-fail to get a non-zero exit code on such problems.",
            err=True,
        )



if __name__ == "__main__":
    main()
