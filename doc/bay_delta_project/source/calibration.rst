Calibration and Versioning
==========================

Calibration
-----------

The main source of information about our calibration thus far is 
the draft 
`2014 Annual Report Chapter 7 <https://msb.water.ca.gov/documents/86683/266737/annual_report_2014_ch7_draft.pdf>`_ 
on SELFE. A more detailed report is forthcoming. For those interested in results from August 2013-2014 drought modelling, 
we can offer time series results at most stations of interest and are working on a presentation.

The August-January 2013 part of this simulation was heavily scrutinized 
and certainly does not qualify as "validation quality" result. 
The rest of the run is pretty hot off the press
and we were satisfied with the results except in a few locations. The strengths and
weaknesses of the results are similar to those described in the Annual Report Chapter.
Some steps were needed to prevent overintrusion of salt into the Delta. These will
be described fully in the more detailed report.

So far we have modeled 2009-2010, Winter 2010-2011 (Bay only) and late 2013-2014. Except for early 2011, these periods mainly reflect low flow periods. Right now we are working on the flooding period of 1997.

In a companion project, we have worked with contractors at RMA in the last two years producing Python tools for harvesting cross-sectional velocity data from ADCP instruments. Our goal with that project is to leverage information that is already being produced during flow station calibrations and special studies to better understand cross-sectional variation in velocity structure and compare it to model results. The project `ADCPy <https://github.com/esatel/ADCPy>`_ has been open-sourced, and is functional and documented for downward looking RDI flow instruments, which are the main ones used by both USGS and DWR for flow calibration. We have some usability enhancements in mind for the next year, and are adding additional instruments (RiverRay, SL-ADCP).

Versioning
----------

At the present rate, we are updating the mesh approximately 2-3 times per year. 
In 2015, we expect announcement of two improvements: improved efficiency from
vertical coordinates and quadrilaterals. We also are looking forward to a greater
consistency between the OHSU and VIMS branches of SELFE and a transition to the 
GNU Public License. 
Each version of the model, inputs and mesh will be carefully 
marked so that archivable and reproducible 
simulations are possible. We will maintain a Bay-Delta user list and will gladly
inform you of new versions. Tell us who you are!



