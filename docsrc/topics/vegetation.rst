

==========
Vegetation
==========

Aquatic Vegetation in SCHISM
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In Bay-Delta SCHISM, the modeling of submerged aquatic vegetation (SAV)
is on by default, with data in or approximations in 
Franks Tract, Cache Complex, South Delta.

SCHISM has a submerged aquatic vegetation module  introduced by :cite:p:`zhang_simulating_2020`, and covered in 
online manual which includes the effects of drag within the canopy, 
and simple representation of turbulence production. Biogeochemical linkages (shading, nutrient competition) are also included 
in the water quality/ecological modules. In the instances where we have introduced vegetation (Cache Complex, Franks Tract, South Delta, Sherman Lake)  it has helped reproduced the distribution of physical flow.

SCHISM can model submerged vegetation (example: Egeria Densa) or with a suitably high 
canopy emergent vegetation vegetation, such as tule. Primrose can also be 
approximated as emergent. Accommodation must be made for patchy floating species such 
as hyacinth.


In SCHISM, vegetation is enabled using the parameter isav=1 in the control file param.nml. For turbulence production
the native "SCHISM" turbulence closures must be used, not GOTM.

.. list-table:: Vegetation Files
   :widths: 25 25 50
   :header-rows: 1

   * - SCHISM file name
     - Example preprocessor name
     - Description
   * - sav_N.gr3
     - sav_density.yaml 
     - stem density per square meter
   * - sav_D.gr3
     - sav_diameter
     - stem diameter
   * - sav_cd.gr3
     - constant
     - coefficient of drag (we currently use 0.20 to 0.28, but see text below)
   * - sav_h.gr3
     - sav_height.yaml
     - canopy height


The first three parameters are multiplied by one another. There is rarely enough data to make them 
statistically identifiable individually, a point revisited below. 
Canopy height is from the bed. We usually assume the canopy reaches -0.15cm NAVD in the main Delta.
which is a compromise based on the fact that apparent effective density diminishes in the upper centimeters.

Approximations and preprocessor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key challenges when modeling vegetation with SCHISM are:

  #. data coverage
  #. interpretation of data as effective density
  #. including enough vertical resolution to allow a boundary layer over the vegetation


Effective Stem Density
^^^^^^^^^^^^^^^^^^^^^^

Because we usually don't have detailed knowledge of the drag coefficient diameter and stem density
and because they all end up multiplied by one another, there is effectively 
a single degree of freedom when it comes to the overall density of the vegetation field. 

We fix the diameter and density and use an "effective stem density" that accounts for variation in drag,
subgrid heterogeneity of the field as well as point values of stem density. In the past we have used
stem densities of 10-30 per meter squared (lower-medium) and 30-60 per meter squared (heavy) coupled with a drag
coefficient of 0.20 to 0.26. You may see legacy files where the stem density is much lower and the drag higher, but
the product in this case is the same general magnitude. For instance, for a fixed diameter 8 stems/m^2 and drag 1.13 
give the same product as instead of 20-60 stems/m^2 and drag 0.28. 

At times when remote sensing was not available, the template included estimates based on heuristics about depth, 
using only one high and one low value, consistent for the most part with the :cite:p:`durand_2016` 
conclusion that most Egeria densa grew between depths of 2m and -1m MLLW and assuming that density is higher in water that
is less than 0.9m at low water. 
 
In areas where we have imagery, we use processed Normalized Density Vegetation Index from the Ustin lab at UC Davis. 
More properly, these are modified NDVI (mNDVI) with more attention in the margins of the 
red band and slightly lower values than ordinary NDVI. The NVDI image is often the best 
source of information on spatial distribution of effective density. However, NDVI is not
as accurate in the water as it is for terrestrial vegetation. Absolute values 
vary between captures so there is still a reliance on field descriptions and a degree of fitting on overall strength
based on looking at the histogram and breaking it into a "no", "low" and "high" bracket.
The "no vegetation" or zero density is typically assigned for mNDVI < -0.05, but for some 
images histogram is clustered at lower values. 


.. code-block:: console

    - attribute: raster_to_nodes.raster_to_nodes(mesh, nodes_sel, '//path/to/delta_NDVI.tif',
        bins=[-998.,-0.2,0,0.4,1.0], 
        mapped_values=[-999., 0., 10., 30., 60., -999.],
        mask_value=0.,
        fill_value=-0.21)
      name: Clifton Court
      type: none
      imports: schimpy.raster_to_nodes   
      vertices:
      - - 622760.2566469825
        - 4191499.7722536493
        ....
        
The :external:py:func:`schimpy.raster_to_nodes.raster_to_nodes` manual page has more info on this function. Index `i` in the 
mapped values is applied between `i-1` and `i` in the bins. The mapped values have to be larger than the number of bins,
which is an artifact of the numpy digitize method used to implement the function.
 
Height 
^^^^^^

Template formulas usually enforce a minimum height of (say 0.25m below), 
a maximum (say 1.0m below) and assume that the vegetation grow to a effective height that reaches just 
below a typical low water mark, slightly lower than the highest whorl you'd see in a boat). 
Here is a sample from `sav_height.yaml`:

.. code-block:: console

   - name: Franks Tract
     type: none
     attribute: 'max(0.25,min(1.0,z-0.01))'
     vertices:
        ... coordinates

When a mix of emergent and submerged vegetation is required, a more complex formula is required. Emergent
vegetation is represented using exaggerated height.









