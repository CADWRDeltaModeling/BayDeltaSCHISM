from setuptools_scm import get_version
from setuptools import setup

# setup.py only needed for conda to resolve versioning
# DO NOT ADD ANYTHING ELSE HERE

setup(
    name="bdschism",
    version=get_version(),
)
