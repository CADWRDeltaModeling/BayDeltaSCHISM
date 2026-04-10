# scripts/install_docs_extras.py

"""This script is used by the documentation action on GitHub
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

# Packages that must be installed via pip (not available in conda-forge)
PIP_ONLY = {
    "sphinxcontrib-xlsxtable",
}

try:
    import tomllib  # Py>=3.11
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tomli"])
    import tomli as tomllib

# Load the pyproj.toml to get the list of extra dependencies for documentation
# Form of this assumes py>=3.11
pp = pathlib.Path("./bdschism/pyproject.toml")
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


all_pkgs = sorted({to_conda_name(s) for s in docs if s})
conda_pkgs = [p for p in all_pkgs if p not in PIP_ONLY]
pip_pkgs = [p for p in all_pkgs if p in PIP_ONLY]

if conda_pkgs:
    print("Installing docs extras via conda:", conda_pkgs, flush=True)
    subprocess.check_call(["micromamba", "install", "-y", "-c", "conda-forge", *conda_pkgs])
else:
    print("No conda packages to install.", flush=True)

if pip_pkgs:
    print("Installing docs extras via pip:", pip_pkgs, flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", *pip_pkgs])
else:
    print("No pip-only packages to install.", flush=True)

if not all_pkgs:
    print("No [project.optional-dependencies].docs group found; skipping.", flush=True)
