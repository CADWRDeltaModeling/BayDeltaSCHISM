

============================
Submerged Aquatic Vegetation
============================

Vegetation in SCHISM
^^^^^^^^^^^^^^^^^^^^
In Bay-Delta SCHISM, the modeling of SAV is on in most runs by default, with data in or approximations in 
Franks Tract, Cache Complex, South Delta.

SCHISM has a submerged aquatic vegetation module  introduced by :cite:p:`zhang_simulating_2020`, and covered in 
online manual which includes the effects of drag within the canopy, 
and simple representation of turbulence production. Biogeochemical linkages (shading, nutrient competition) are also included 
in the water quality/ecological modules. In the instances where we have introduced vegetation
 (Cache Complex, Franks Tract, South Delta, Sherman Lake)  it has helped reproduced the distribution of physical flow.

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
     - coefficient of drag (we use 1.13)
   * - sav_h.gr3
     - sav_height.yaml
     - canopy height


The first three parameters are multiplied by one another. There is rarely enough data to depict them all, 
a point revisited below. Canopy height is from the bed. We usually assume the canopy reaches -0.25cm NAVD
which is a compromise based on the fact that apparent effective density diminishes in the upper centimeters.

Approximations and preprocessor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key challenges when modeling vegetation with SCHISM are:

  #. sufficiency of data and converting to useful parameters and
  #. need to include sufficient vertical resolution to allow a boundary layer over the vegetation

Done right, strong shear above and below the canopy can be obtained. Done crudely, the approximation is nothing 
more than an added body force inducing a kind of "friction" over the entire water column that is lacking in
3D models (roughness is just at the bed).



Effective Stem Density
^^^^^^^^^^^^^^^^^^^^^^

Given lack of detailed knowledge of the drag coefficient diameter and stem density, there is effectively 
a single degree of freedom. We fix the diameter and density and use what is effectively an 
"effective stem density" that tries to take into account most of the spatial variation. 

The template has formulas for effective density based on depth using high and low values only, 
consistent for the most part with the :cite:p`university_of_california_davis_physical_2016` 
conclusion that most Egeria densa grew between depths of 2m and -1m MLLW. 
 
In areas where we have imagery, we use processed Normalized Density Vegetation Index from the Ustin lab at UC Davis. 
These are, we hope, representative, although we do not swap them out for particular years unless the role
of vegetation pattern is the focus of investigation. The images give a good relative sense of density and
have also been used to categorize vegetation. Each image is usually examined as a histogram, as the absolute
value of NDVI relative to visual ground truth tends to drift. A "no vegetation" level is typically assigned for
values less than a threshold around -0.05, but as you can see from the bin value -0.2 things were adjusted downward
and we have noticed that in Clifton Court in particular submerged vegetation seems to be observed for NDVI lower than the 
"classic" low end values. High values are often NDVI > 0.2 but again the scale is shifted down a bit below. We
do not bin or assign values in away that is much more specific than none-low-high or none-low-medium-high.


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
 
Height 
^^^^^^

Template formulas usually enforce a minimum height of (say 0.25m below), 
a maximum (say 1.5m below) and assume that the vegetation grow to a height that reaches just 
below a typical low water mark where we assume 0.4m NAVD is a good generic 
low water mark. Here is a sample from `sav_height.yaml`:

.. code-block:: console

   - name: Franks Tract
     type: none
     attribute: 'max(0.25,min(1.5,z+0.25))'
     vertices:
        ... coordinates

When a mix of emergent and submerged vegetation is required, a more complex formula is required. Usually emergent
vegetation is represented as a very high value.









