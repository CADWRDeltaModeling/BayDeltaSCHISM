from setuptools import setup
import versioneer

requirements = [
    schimpy,
    vtools,
    dms_datastore
]

setup(
    name='repository-name',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Tools for launching and evaluating Bay-Delta SCHISM runs",
    license="MIT",
    author="Eli Ateljevich",
    author_email='Eli.Ateljevich@water.ca.gov',
    url='https://github.com/water-e/repository-name',
    packages=['bdschism'],
    
    install_requires=requirements,
    keywords='repository-name',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
