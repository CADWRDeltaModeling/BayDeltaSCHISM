import os
from dynaconf import Dynaconf

def get_settings(env="default"):
    # Paths
    package_default_config = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    local_config = os.path.join(os.getcwd(), "proj_config.yaml")
    env_config = os.getenv("MYPROJ_CONFIG")  # Custom config from environment variable

    # Configuration hierarchy
    config_files = [package_default_config]  # Default package config
    if os.path.exists(local_config):
        config_files.insert(0, local_config)  # Project-level config
    if env_config and os.path.exists(env_config):
        config_files.insert(0, env_config)  # Custom config via MYPROJ_CONFIG

    # Load settings
    settings = Dynaconf(settings_files=config_files, environments=True, env=env)

    # Log configuration source
    print(f"Using configuration from: {config_files[0]} current env {settings.current_env}")

    return settings
