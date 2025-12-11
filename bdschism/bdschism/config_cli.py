import click
import yaml
from pathlib import Path

from bdschism.settings import get_settings


# Project-level config file in the current working directory
PROJECT_CONFIG = Path("bds_config.yaml")


def _load_project_yaml():
    """
    Load the project-level bds_config.yaml if present, else {}.
    """
    if PROJECT_CONFIG.exists():
        with PROJECT_CONFIG.open("r") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise click.ClickException(
                    f"{PROJECT_CONFIG} must contain a mapping at top level."
                )
            return data
    return {}


def _write_project_yaml(data):
    """
    Write project configuration back to bds_config.yaml.
    """
    with PROJECT_CONFIG.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


@click.group(
    help="Inspect or modify project-level bdschism configuration (bds_config.yaml)."
)
def config_cli():
    """Subcommands: get, set, unset."""
    # Nothing to do here; subcommands are defined below.
    pass


@config_cli.command("get")
@click.argument("key")
def config_get(key):
    """
    Print the effective value of KEY from merged bdschism settings.

    This uses get_settings(), so it reflects package defaults, project bds_config.yaml,
    and any BDS_CONFIG override.
    """
    settings = get_settings()
    try:
        value = getattr(settings, key)
    except AttributeError:
        raise click.ClickException(f"Key '{key}' not found in effective settings.")
    click.echo(value)


@config_cli.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """
    Set KEY=VALUE in the project-level bds_config.yaml.

    Creates the file if it does not exist.
    """
    data = _load_project_yaml()
    data[key] = value
    _write_project_yaml(data)
    click.echo(f"Set {key}={value} in {PROJECT_CONFIG}")


@config_cli.command("unset")
@click.argument("key")
def config_unset(key):
    """
    Remove KEY from the project-level bds_config.yaml.
    """
    data = _load_project_yaml()
    if key not in data:
        raise click.ClickException(f"Key '{key}' not present in {PROJECT_CONFIG}")
    del data[key]
    _write_project_yaml(data)
    click.echo(f"Removed {key} from {PROJECT_CONFIG}")
