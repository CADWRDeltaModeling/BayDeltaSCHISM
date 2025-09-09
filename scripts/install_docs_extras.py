# scripts/install_docs_extras.py

""" This script is used by the documentation action on GitHub
    for installing dependencies (e.g. sphinx extensions) 
    that are listed in the doc section of optional dependencies 
    in pyproject.toml. The script uses conda to do the install,
    which allows the building of a complete environment for 
    sphinx to use for references and introspection. At the current time,
    the Cheese shop lacks some items. 
"""
import sys, subprocess, pathlib

# Mappings between PYPI and conda
NAME_MAP = {
    "Pillow": "pillow",
    "netCDF4": "netcdf4",
}

try:
    import tomllib  # Py>=3.11
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tomli"])
    import tomli as tomllib

# Load the pyproj.toml to get the list of extra dependencies for documentation 
# Form of this assumes py>=3.11
pp = pathlib.Path("pyproject.toml")
with pp.open("rb") as f:
    data = tomllib.load(f)  # works for tomllib and tomli

proj = data.get("project", {})
extras = proj.get("optional-dependencies", {})
docs = extras.get("doc", [])
if isinstance(docs, str):
    docs = [docs]

def to_conda_name(spec: str) -> str:
    name = spec.split()[0]
    name = name.split(";")[0]
    name = name.split(">=")[0].split("==")[0].split("~=")[0].split("<")[0]
    return NAME_MAP.get(name.strip(), name.strip()).lower()

pkgs = sorted({to_conda_name(s) for s in docs if s})
if pkgs:
    print("Installing docs extras via conda:", pkgs, flush=True)
    subprocess.check_call(["micromamba","install","-y","-c","conda-forge", *pkgs])
else:
    print("No [project.optional-dependencies].docs group found; skipping.", flush=True)
