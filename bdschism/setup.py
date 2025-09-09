from setuptools_scm import get_version
from setuptools import setup, find_packages

# setup.py only needed for conda to resolve versioning
# DO NOT ADD ANYTHING ELSE HERE

setup(
    packages=find_packages(include=["bdschism", "bdschism.*"]),
    # version is managed by setuptools_scm via pyproject.toml
)
