from setuptools import setup
import versioneer

requirements = [
    schimpy,
    suxarray,
    vtools,
    dms_datastore
]

setup(
    name='repository-name',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Tools for launching and evaluating Bay-Delta SCHISM runs",
    license="MIT",
    author="California Department of Water Resources",
    author_email='Eli.Ateljevich@water.ca.gov',
    url='https://github.com/water-e/repository-name',
    packages=['bdschism'],

    install_requires=requirements,
    keywords='repository-name',
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ]
)
