Using Python Pre-processing Tools Directly
============================================
If users are familiar with Python, various jobs with SCHISM meshes can be done by programming functions in the tool directly.

Reading a Mesh in GR3
---------------------
The first step to manipulate or do jobs with a mesh is reading in a mesh. A mesh can be read in with :meth:`~selfe_utility.load_gr3`. This function returns a SELFE input instance. A mesh is an attribute of the SCHISM input class, and the mesh can be accessed by :attr:`~selfe_utility.SelfeUtility.mesh`. This mesh is an instance of :class:`~selfe_mesh.SelfeMesh` which is in turn an extension of :class:`~trimesh.TriMesh`. TriMesh is a slimmed version of 'trigrid' by Rusty Collerman with some modifications. See the API references for methods.