
_preprocessor:

Preprocessing
==============

Invoking the preprocessor
-------------------------

prepare_SCHISM.py
^^^^^^^^^^^^^^^^

.. argparse::
    :module: prepare_schism
    :func: create_arg_parser
    :prog: prepare_schism.py


Input Files
-----------

Information in the input files of the pre-processor are provided in geophysical coordinates.  This information will be translated into SCHISM native input, which are based on node and element indices. 

The pre-processing input uses the human-readable YAML format.  See the `YAML <http://en.wikipedia.org/wiki/YAML>`_ Wikipedia page for an introduction. 
YAML format is intuitive and you probably can learn it from copying and and modifying sample inputs.
A few key things about YAML syntex include:

* Indentation by whitespace is used to denote structure. Tabs are not allowed -- many text editors such as notepad++ have a "replace tabs with spaces" type of option. As with Python itself, the amount of indentation is important to the correctness of the data hierarchy.
* Comments begins with #. It can start anywhere on a line and comments out the rest of the line.
* Associative arrays are denoted using the colon space (: ) and forms key: vaule, which is a hash table/dictionary/mapping in effect.

Main Input File
^^^^^^^^^^^^^^^
The main input contains multiple blocks each of which either points to subordinate input files or 
explicitly assigns values. We typically use the file name *input.yaml*. There are many potential
functions you can list in the main input file, but most of these other than an input mesh are optional 
-- it is perfectly acceptable to use the preprocessor as a way to launch an individual task.

Mesh
''''

This section guides the conversion of a mesh from SMS format and the assignment and optimization
of depths. The section can have five items as shown below:

.. code-block:: yaml

  mesh:
    mesh input file:         baydelta71.2dm
    dem list file:           dem_71.txt
    depth optimization file: depth_opt_params.yaml
    open boundary file:      open_boundary.yaml
    gr3 output file:         baydelta71opt.gr3
    ll output file:          hgrid.ll

The items in this section are as follows: 

mesh input file 
  an original mesh input file either in 'gr3' or SMS '2dm' file format. If the file name has the extension of '.2dm,' it will be converted into a 'gr3' format file with the same file name, e.g. 'baydelta71.gr3' in the example above, and the gr3 file will be read in for further processing. 
  
dem list file  
  If 'dem list file' is provided, elevation information from the DEM files in the list will be used to populate elevation at the nodes of the mesh. See :ref:`dem_list_file` for more on the format. 

open boundary file
  lists open boundary locations. See :ref:`openboundary_input` for more.  
  
depth optimization file
  lists parameters for depth optimization of the mesh. See :ref:`depth_optimization_parameter_file` for more. 
  
gr3 output file
  is an output file name of the mesh after pre-processing

ll output file
  The ll (lower case LL) is an output file name of the mesh in longitude and latitude coordinates.

The item, 'mesh input file', must be provided, but the others are optional. If an item is missing, a corresponding job is not conducted, e.g. 'depth optimization file' is not given, the optimization will not run.


Variable Substitution
'''''''''''''''''''''

The main input supports substitution of variables. Variables defined in the env section will be substituted in any variables in the other sections. In an example shown below,

.. code-block:: yaml

  env:
    input_dir: ../run71
  mesh:
    mesh input file: ${input_dir}/bay_delta.gr3

the value of 'mesh input file' becomes *../run71/bay_delta.gr3* after substitution. The
variable name for replacement should be denoted with $ sign and curly braces as shown in the example.


Generate gr3 with Constant
''''''''''''''''''''''''''

SCHISM uses the gr3 format for spatial input specified at nodes. The main horizontal grid file *hgrid.gr3*
is in a slightly extended form of this format that includes boundary specifications. For other spatial data, 
the z or value column could specify roughness, diffusivity or other spatial parameters.

The section 'gr3 with constant' creates these file by assigning :

.. code-block:: yaml

  gr3 with constant:
    xlsc.gr3: 0.1
    diffmax.gr3: 1.0
    windrot_geo2proj.gr3: 0.0
    manning.gr3: 0.025
    rough.gr3: 0.007

This section creates gr3 files that have the same mesh structure and coordinates as the final output mesh, but the original depth values will be replaced with constants given in this section as properties assigned at nodes. For example, 'xlsc.gr3: 0.1' will create a gr3 file name 'xlsc.gr3' that has the same mesh information but the z-values of all nodes will be set to 0.1.


Generate gr3 from polygons 
''''''''''''''''''''''''''''

It is also possible to create a gr3 format file using polygons, assigning values using a formula or constant within
each region.:

.. code-block:: yaml

  gr3 with polygons:
    hgrid.gr3: deepening_72.yaml
    estuary.gr3: estuary.yaml
    elev.ic: elev.yaml
    s_nudge.gr3: nudge.yaml
    t_nudge.gr3: nudge.yaml
    diffmin.gr3: diffmin.yaml

Similar to the previous section 'gr3 with constant,' this section creates gr3 files that have the same mesh structure and horizontal coordinates as the final output mesh but with modified depth values specified in polygon files. A polygon file can have multiple polygons with constants or equations. See the format of the :ref:`polygon_input` for further information.


Generate prop with Polygons
'''''''''''''''''''''''''''''

The *.prop file differs from the *.gr3 file in that it is element centered. The 'prop with polygons' section
generates these files from regions delineated by polygons:

.. code-block::yaml

  prop with polygons:
    tvd.prop: tvd.yaml

When any of nodes of an element falls in a polygon, the element will get the attribute of the polygon. The output file format, 'prop' contains properties of elements of the mesh without mesh information whereas 'gr3' format can have only nodal properties (usually depth) with mesh information. A typical prop input is 'tvd.prop' designating where TVD will be applied.



Hydraulic Structures
''''''''''''''''''''

The next section in the main input is 'hydraulics'. It has two sets of items: 'input file' and 'output file' as shown below. The scripts reads structure locations and configuration from the input file, and creates SCHISM native hydraulics structure input file. See the detail of the hydraulic structure input file at :ref:`structure_input`.

.. code-block:: yaml

  hydraulics:
    input file:  hydraulics.yaml
    output file: hydraulics.in


Source/Sink
'''''''''''

The next section is 'source/sink.' It has two sets of items similarly to 'hydraulics': 'input file' and 'output file' as shown below. See the detail of source/sink input file at :ref:`sourcesink_input`.

.. code-block::yaml

  source/sink:
    input file: source_sink.yaml
    output file: source_sink.in


Flow Output Requests
''''''''''''''''''''

The last section is 'flow output.' It has two sets of items similarly to the previous block: 'input file' and 'output file' as shown below. See the details of the format of the input at :ref:`flowoutput_input`.

.. code-block:: yaml

  flow output:
    input file: flowlines.yaml
    output file: fluxflag.prop


Complete Example
''''''''''''''''

An example of a whole main input is shown below:

.. code-block:: yaml

  # Input intended for year 2009 run with mesh ver 71.
  env:
    input_dir: ../run71
  mesh:
    mesh input file:         ${input_dir}/baydelta71.2dm
    dem list file:           dem_71.txt
    open boundary file:      open_boundary_71.yaml
    depth optimization file: depth_opt_params.yaml
    gr3 output file:         baydelta71opt.gr3
    ll output file:          hgrid.ll
  gr3 with constant:
    hgrid.gr3:   deepening_71.yaml
    elev.ic:     elev.yaml
    estuary.gr3: estuary.yaml
    s_nudge.gr3: nudge.yaml
    t_nudge.gr3: nudge.yaml
    diffmin.gr3: diffmin.yaml
  gr3 with polygons:
    estuary.gr3: ${input_dir}/estuary.yaml
    elev.ic:     ${input_dir}/elev.yaml
  prop with polygons:
    tvd.prop:    ${input_dir}/tvd.yaml
  hydraulics:
    input file:  hydraulics.yaml
    output file: hydraulics.in
  source/sink:
    input file:  ${input_dir}/source_sink_mod.yaml
    output file: source_sink.in
  flow output:
    input file:  ${input_dir}/flowlines.yaml
    output file: fluxflag.prop


.. _dem_list_file:

DEM List File
^^^^^^^^^^^^^

This file is a simple text file containing a list of DEM files in tiff format. Each line is one file name with path information. See the example below.

.. code-block:: txt

  ../bathymetry/dem_false_river_2m_20140322.tif
  ../bathymetry/dem_fishermans_cut_2m_20140322.tif
  ../bathymetry/dem_sutter_slough_2m_20140322.tif
  ../bathymetry/dem_steamboat_2m_20140322.tif
  ../bathymetry/dem_columbia_cut_2m.tif
  ../bathymetry/dem_georgiana_slough_2m.tif
  ../bathymetry/dem_miner_slough_2m.tif
  ../bathymetry/dem_mokelumne_river_2m.tif

The DEM list is used to retrieve elevation at nodes or quadrature points of the mesh processing and grid optimization. The ordering of the DEM files matters because upper ones in the list will be used first and lower ones will fill area where the upper ones do not cover consecutively.


.. _depth_optimization_parameter_file:

Depth Optimization Parameter File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This file contains for parameters for depth optimization. See the depth optimization documentation for details.

.. code-block:: yaml

  damp: 0.2
  damp_shoreline: 10.0
  face_coeff: 1.0
  volume_coeff: 1.0


.. _openboundary_input:

Open Boundary Input
^^^^^^^^^^^^^^^^^^^
Typically a domain of a open water body has multiple open boundaries such as oceans or rivers. SCHISM needs to know the locations of those open boundaries in the list of node indices. This tool generates a string of boundary nodes from two sets of coordinates, which represent both ends of an open boundary.

Each section name in the file is a name of an open boundary, and the four following values represents two pairs of x and y coordinates for the ends of the open boundary. They do not needs to be in one line or two. It is recommended to write the ordering of the open boundaries and two pairs of each open boundary in counter-clockwise fashion.

.. code-block:: yaml

  # Open Boundary input sample
  ocean:
    503363 4204253
    550710 4139854
  coyote:
    591817 4146720 591796 4146806


.. _polygon_input:

Polygon Input
^^^^^^^^^^^^^
The polygon input format is used to specify certain values at regions covered by polygons. The use cases are: deepening or imposing minimum depth in some regions, setting up initial values, setting nudging factors, and etc.

The format can start with a default value. If the default value is given, the value is filled in the area that is not covered by any of the polygons in the polygon file. If the default value is not given, the original value from the mesh, which is typically depth, is kept.

Each polygon entry starts with a name of a polygon in 'polygons' section and can have three key-value pairs: attribute, type, and vertices.


Attribute
'''''''''

The item, 'attribute' is a constant value or an equation associated with the polygon. The equation follows Python syntax. In equation, you can use three variables, x, y, and z, which are coordinates of nodes. See an example of the equation use below.


Type
''''

The item, 'type' is optional. Possible values for 'type' are 'max,' 'min,' and 'none.' If the value is not given, it is assumed 'none.' When 'type' is 'min,' the given value is compared with current values (depth) at nodes in the polygon in the mesh, and the given value will be used when the depth value is smaller that the given value in order to impose minimum depth (or value.) When 'type' is 'max,' vice versa. When 'type' in 'none,' the given value will be used.

Vertices
''''''''
The item, 'vertices' are a list of pairs of x and y coordinates of vertices of the polygon. See an example below:

.. code-block:: yaml

  default: 1
  polygons:
    coyote:
      attribute: 3
      type: min
      vertices:
        588675 4147370
        588601 4146687
        590432 4145967
        592217 4146521
        592120 4147029
    confluence:
      attribute: min(1, 1. + 178e3 * (x - 597183) * (614983 - x))
      vertices:
        600027 4217705
        599456 4215990
        599265 4214179
        598598 4213178

In this example, nodes in the area that are not covered by the two polygons will be filled with the default value of one. The first polygon, 'coyote,' uses a constant value of three to give minimum value in the polygon area. The second polygon, 'confluence,' uses an equation.

.. _structure_input:

Hydraulic Structures Input
^^^^^^^^^^^^^^^^^^^^^^^^^^
The hydraulic structures module allows structures to be superimposed on the mesh, effectively substituting a coupled boundary condition based on a flow equation for a weir, gate or culvert.
See an example below, as well as the pdf guide to hydraulic structures in SCHISM which contains detailed information on the structure types that
are supported.

The preprocessor can assign data to hydraulic structures based on geophysical coordinates.  
The first value in the output file is the global 'nudging,' and it is a relaxation constant that determines how fast calculated flow of a structure is imposed. The next section, 'structures,' lists input data for each hydraulic structure in 'blocks'. Each structure block starts with the name of the structure. You should use a structure name without white spaces because this name will be used to link to a time series file name.

The subsequent lines describe the type, configurations, location (line segment), and the reference nodes of the structure. The last item, reference, is optional; it refers to the location that is used
to assess water levels for purposes of calculating structure flow.

SCHISM supports six types of hydraulic structures: 'radial' for radial gates, 'radial_relheight' for radial gates with linear coefficient, 'culvert' for fully submerged pipes/culverts/orifices, 'weir' for weirs or submerged barriers, 'orifice' for rectangular orifices, and 'transfer' for water transfer. Each structure comes with a line segment in 'line' and physical configurations of it. The two end points of the line segment must be outside of the mesh to block a cross-section of a channel completely. Otherwise, the structure will be leaky and will not work properly.

Different structure type requires slightly different physical configuration parameters.  Common parameters for all structure types except 'transfer' are 'n duplicates', 'elevation,' 'width,' 'coefficient', 'op downstream,' 'op upstream,' and 'use time series.' For 'radial' and 'orifice', 'height' is required. For 'radial_relheight', additional 'coefficient height' is required on top of values for 'radial.' For 'culvert', 'radius' is required. Structure 'transfer' needs only two parameters: 'flow' and 'use time series.'

The item, 'reference' in a structure describes where up/downstream elevation is assessed for calculating the structure flow using a weir/culvert/gate equation. The parameter is optional; if it is omitted, the default is 'self.'  If this value is 'self,' a pair of reference nodes will be selected on each side of the current structure will be used for calculation of structure flows. If a name of another structure is given for the reference, the reference nodes of that structure are used. For example below, 'grantline_culvert' uses the surface elevation from the reference node pairs of 'grantline_weir.'

.. code-block:: yaml

  # Hydraulic Structure Sample
  nudging: 0.1
  structures:
    ccfb_gate:
      type: radial_relheight
      line:
        626980 4187907
        627006 4187944
      configuration:
        n duplicates: 5
        elevation: -10.0
        width: 10.0
        height: 10.0
        coefficient: 1.0
        coefficient height: 0.1
        op downstream: 1.0
        op upstream: 1.0
        use time series: 1
      reference: self

    montezuma_radial:
      type: radial
      line:
        597636 4216735
        597664 4216756
      configuration:
        n duplicates: 3
        elevation: -6.86
        width: 10.97
        height: 10.0
        coefficient: 1.0
        op downstream: 1.0
        op upstream: 1.0
        use time series: 1
      reference: self

    grantline_weir:
      type: weir
      line:
        636576 4186940
        636575 4187000
      configuration:
        n duplicates: 1
        elevation: 1.00
        width: 54.9
        coefficient: 0.8
        op downstream: 1.0
        op upstream: 1.0
        use time series: 1
      reference: self

    grantline_culvert:
      type: culvert
      line:
        636576 4186918
        636576 4186940
      configuration:
      n duplicates: 6
      elevation: -1.28
      radius: 0.61
      coefficient: 0.6
      op downstream: 0.0
      op upstream: 1.0
      use time series: 1
    reference: grantline_weir


.. _sourcesink_input:

Source/Sink Input
^^^^^^^^^^^^^^^^^
The source/sink input for the pre-processing has two sections, 'sinks' and 'sources,' and each section simply has list of name and location pairs. Each location of source/sink will be translated into an element index. If a source or sink location does not fall in the mesh, the script automatically finds the nearest element from it and assign the source or sink to the element.

Users must provide time series files, 'vsource.th' and 'vsink.th' for the amount of the source and sink flow in the same ordering that is presented in this input. For source flows, salinity and temperature of the flows need to be provided in 'msource.th' in the same ordering of sources in this input.

.. code-block:: yaml

  # Source/sink sample
  sinks:
    dicu_div_1: 653567.0902   4172012.544
    dicu_div_3: 652136.6707   4176150.845
  sources:
    dicu_drain_1: 653567.0902 4172012.544
    dicu_drain_3: 652136.6707 4176150.845

.. _flowoutput_input:

Flow Output Input
^^^^^^^^^^^^^^^^^
The flow output input simply comprises a list of line segments paired with the names of output locations as shown below. The ordering of the end points of the line segment decides the orientation of the flow output. As you face the nominal downstream
direction of the flow output, the starting coordinate is on your left and the ending on your right. Two end points of a line segment should be outside of the mesh to make sure the flow line segment is not leaky.

.. code-block:: yaml

  # Flow output location sample
  Steamboat Slough: 624472.3676 4240454.635 624427.4511 4240509.007
  Threemile Slough: 614040.1649 4218203.329 614108.8814 4218393.771

