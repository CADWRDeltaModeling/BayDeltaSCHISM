__author__ = """Eli Ateljevich, Kijin Nam"""
__email__ = "Eli.Ateljevich@water.ca.gov; Kijin.Nam@water.ca.gov"

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from pkg_resources import get_distribution, DistributionNotFound

    def version(pkg):
        return get_distribution(pkg).version

    PackageNotFoundError = DistributionNotFound

try:
    __version__ = version("bdschism")
except PackageNotFoundError:
    # Fallback for running from a VCS checkout without installation
    try:
        from setuptools_scm import get_version

        __version__ = get_version(root="..", relative_to=__file__)
    except Exception:
        __version__ = "unknown"
