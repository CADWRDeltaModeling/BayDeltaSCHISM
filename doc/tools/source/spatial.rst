
SELFE Spatial Data
==================

Formats
--------------
SELFE requires numerous spatial inputs, including node and element-centered properties, hydraulic structures specifications, output locations and so on. Under the native SELFE input system, some of these spatial inputs are expected in node or cell indices rather than geophysical coordinates. Hence, the user must convert spatial information of the model in geophysical coordinates into corresponding node and cell indices. Also it means that whenever changes are made in the model mesh, it often leads to renumbering of node and cell indices, and all spatial inputs are updated accordingly. Doing this input conversion of spatial input information manually from geophysical coordinates to node and cell indices in a large mesh is not only very cumbersome but also very error-prone.

To make this spatial input preparation easy and reproducible with information in geophysical coordinates, a suite of Python scripts are developed. 



