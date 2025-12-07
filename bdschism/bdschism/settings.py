import os
import shutil
import platform
from dynaconf import Dynaconf
from pathlib import Path


def get_settings(config_log: bool=False):
    """
    Load and return application settings from a configuration file.

    This function retrieves configuration settings using a hierarchy of possible sources:
    1. A package-level default configuration file (`bds_config.yaml` within the package).
    2. A project-level configuration file (`bds_config.yaml` in the current working directory).
    3. An environment-specific configuration file, if `BDS_CONFIG` is set and points to a valid file.

    The function uses `Dynaconf` to load settings, ensuring that the highest-priority configuration
    (environment variable, project-level, or package default) is used.

    Returns
    -------
    Dynaconf
        A `Dynaconf` object containing the loaded configuration settings.

    Notes
    -----
    - The package-level configuration file provides default settings.
    - If a project-level configuration file exists in the current directory, it overrides the package default.
    - If an environment variable `BDS_CONFIG` is set and points to a valid file, it takes the highest precedence.
    - The function logs the configuration source being used.

    Examples
    --------
    Load settings from the highest-priority available configuration file:

    >>> settings = get_settings()
    Using configuration from: /path/to/highest-priority-config.yaml current env development

    Access settings:

    >>> settings.some_setting
    'some_value'
    """
    # Paths
    package_default_config = os.path.join(
        os.path.dirname(__file__), "config", "bds_config.yaml"
    )
    local_config = os.path.join(os.getcwd(), "bds_config.yaml")
    env_config = os.getenv("BDS_CONFIG")  # Custom config from environment variable

    # Configuration hierarchy
    config_files = [package_default_config]  # start with lowest precedence

    if os.path.exists(local_config):
        config_files.append(local_config)  # project-level overrides

    if env_config and os.path.exists(env_config):
        config_files.append(env_config)  # env-specific overrides (highest)

    # Load settings
    settings = Dynaconf(settings_files=config_files)

    # Log configuration source
    if config_log == True:
        print(
            f"Using configuration from: {config_files[0]} current env {settings.current_env}"
        )

    return settings


def create_link(source, symlink, config_log=False):
    """
    Create a link between a source file and a target path based on system-specific link styles.

    This function creates a symbolic link, junction, or copies the file, depending on the
    system settings. The link style is determined dynamically from `get_settings()`, which
    specifies the preferred linking method for the operating system.

    Parameters
    ----------
    source : str
        The path to the source file that will be linked.
    symlink : str
        The target path where the link (or copy) will be created.
    config_log : bool, optional
        If True, log the configuration source being used.

    Raises
    ------
    ValueError
        If the link style retrieved from `get_settings()` is unsupported.

    Notes
    -----
    - If a symbolic link already exists at `symlink`, it is removed before creating a new one.
    - On Windows, the function supports creating junction links (`mklink`), symbolic links,
      or copying the file instead.
    - On Unix-based systems, it defaults to using symbolic links.

    Examples
    --------
    Create a symbolic link on Unix-like systems or an appropriate alternative on Windows:

    >>> create_link("/path/to/source.txt", "/path/to/symlink.txt")
    """
    settings = get_settings(config_log=config_log)
    link_style = settings.link_style[platform.system()]

    # remove symlink before setting
    if os.path.islink(symlink):
        os.remove(symlink)

    # set the symlink based on operating system spec
    if link_style == "symlink":
        os.symlink(source, symlink)
    elif link_style == "junction":
        os.system(f'mklink "{source}" "{symlink}"')  # Windows junction link
    elif link_style == "copy":
        print(source, symlink)
        shutil.copyfile(source, symlink)  # Windows junction link
    else:
        raise ValueError(f"Unsupported link style: {link_style}")

def interpolate_variables(config_log=False):
    """
    interpolate SCHISM variables from background grid to foreground grid for elevation, tracers, or uv3D

    Parameters
    ----------
    config_log : bool, optional
        If True, log the configuration source being used.

    Raises
    ------
    ValueError
        If the link style retrieved from `get_settings()` is unsupported.

    Notes
    -----
    - `interpolate_variables8` is the version of interpolate_variables associated with SCHISM 5.11

    Examples
    --------
    Interpolate SCHISM variables on Unix-like systems or an appropriate alternative on Windows:

    >>> interpolate_variables()
    """
    import subprocess

    settings = get_settings(config_log=config_log)

    result = subprocess.run(
        settings.interpolate_variables,
        shell=True,          # keeps behavior similar to os.system
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "interpolate_variables command failed:\n"
            f"  Command: {settings.interpolate_variables}\n"
            f"  Exit code: {result.returncode}\n"
            f"  Stdout:\n{result.stdout}\n"
            f"  Stderr:\n{result.stderr}"
        )

def get_output_from_interpolate_variables(varname, config_log=False):
    """
    Get the output filename for the interpolate_variables function.

    Parameters
    ----------
    varname : str
        The variable name for which to retrieve the output filename (e.g., 'uv3d').
    config_log : bool, optional
        If True, log the configuration source being used.

    Returns
    -------
    str
        The output filename for the interpolate_variables utility.
    """
    settings = get_settings(config_log=config_log)
    return settings.output_from_interpolate_variables[varname]