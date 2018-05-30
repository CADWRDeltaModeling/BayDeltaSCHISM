Introduction
============

Installing the toolset
----------------------

This tool comes with the Bay-Delta modeling package as a 'scripts' directory. 
No installation or compilation is required, but users need to add the 'scripts' directory onto their 'PYTHONPATH' environment variable for Python to be able to find the scripts directory. It is also possible to add the directory to your PATH environment variable so that you can launch the scripts without typing 'python'.

Prerequisites
-------------

The tools are written in Python, and there are a few Python prerequisites.

* `Python <https://www.python.org/>`_: To run this tool, Python is required because Python is . The tool is written in and developed under Python ver 2.7. Using a scientific python distribution such as `pythonxy <https://code.google.com/p/pythonxy/>`_ or `Anaconda <https://store.continuum.io/cshop/anaconda>`_ is strongly recommended because they come with most of prerequisites listed below.
* Vtools: Most of the time series management is done with Vtools. Refer to Vtools documentations for details. Vtools has its own dependencies that are not listed here.
* `Numpy <http::/www.numpy.org/>`_:  Numpy is a Python package for scientific computing. Ver 1.8 is used for the development. Vtools requires Numpy as well.
* `Matplotlib <http://matplotlib.org/>`_: Matplotlib is a Python plotting package. Ver 1.3 is used for the development. Vtools uses Matplotlib as well.
* `Brewer2mpl <https://github.com/jiffyclub/brewer2mpl>`_: This is a a python package to access colorbrewer2.org color map. The color map provides nice sets of color palettes for plotting.
* `Rtree <https://pypi.python.org/pypi/Rtree/>`_: Rtree is a ctypes Python wrapper of libspatialindex that provides a number of advanced spatial indexing features. `libspatialindex <http://libspatialindex.github.io/>`_ is C++ library for spatial index, and it must be installed before installing Python Rtree package. This library is used to geometrical indexing of a mesh in the pre-processing.
* `GDAL <http://www.gdal.org/>`_: A part of the tools uses Python package of GDAL: Geospatial Data Abstraction Library. This Python package depends on libgdal.
* `triangle <http://dzhelil.info/triangle/>`_: Python Triangle is a python wrapper of Jonathan Richard Shewchuk’s two-dimensional quality mesh generator and Delaunay triangulation library.

