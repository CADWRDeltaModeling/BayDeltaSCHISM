

#################
Atmospheric setup
#################

Basic introduction and requirements
-----------------------------------
SCHISM requires air-sea heat flux input to calculate the water temperature. Downward short-wave radiation, long-wave radiation, relative humidity, wind, air temperature and precipitation input are obtained through HRRR (High-Resolution Rapid Refresh) model by NOAA. 



Where are the data?
-------------------

For external users, the data are provided on the CNRA portal page for `SCHISM atmospheric data <https://data.cnra.ca.gov/dataset/bay-delta-schism-atmospheric-collection-v2-0>`_ . Internal DWR users should use shared copies.


Pointing to the data with make_links_full.py
--------------------------------------------

There is a script in bdschism or schimpy called `make_links_full.py`. You have to edit this script to make sense with your directory structure. It maps the names expected by SCHISM to paths of files with more informative names.

