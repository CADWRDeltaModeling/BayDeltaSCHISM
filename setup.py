from setuptools import setup
import versioneer

requirements = [
    # package requirements go here
]

setup(
    name='pyschism',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Scripts for SCHISM pre- and post-processing",
    license="MIT",
    author="Kijin Nam",
    author_email='knam@water.ca.gov',
    url='https://github.com/cadwrdeltamodeling/baydeltaschism',
    packages=['pyschism'],
    
    install_requires=requirements,
    keywords='baydeltaschism',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
