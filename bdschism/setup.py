from setuptools import setup
import versioneer

requirements = [
    'schimpy',
    'suxarray',
    'vtools',
    'dms_datastore',
    'dynaconf'
    
]

setup(
    name='bdschism',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Tools for launching and evaluating Bay-Delta SCHISM runs",
    license="MIT",
    author="California Department of Water Resources",
    author_email='Eli.Ateljevich@water.ca.gov',
    url='https://github.com/CADWRDeltaModeling/BayDeltaSCHISM',
    packages=['bdschism'],
    include_package_data=True,  # Ensure non-code files are included
    package_data={"bdschism": ["config/*.yaml"]},  # Include YAML config
    install_requires=requirements,
    keywords='repository-name',
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    entry_points={
        "console_scripts": [
            "set_nudging=bdschism.set_nudging:main",
            "hot_from_hot=bdschism.hotstart_from_hotstart:main",
            "hot_nudge_data=bdschism.hotstart_nudging_data:main",
            "create_nudging=schimpy.nudging:main"
        ]
    }
)
