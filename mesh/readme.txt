
bay_delta_90e.map contains the map used for ITP.
bay_delta_96.map is identical to 90e_franks_base, which was the final base mesh for Franks Tract Futures
bay_delta_98 was used for DCP sea level rise (including DCP) and will be in a separate branch
bay_delta_110.map is used for the historical retrospective hindcast paper

As of 2/9/2021 not sure what official uses bay_delta_103 and 105 were used for and if there is no official use they could be deleted.


General instructions for building mesh from map:
(note that there is now a video tutorial illustrating this)
1. Select the map coverage that represents the mesh, e.g. bay_delta_96_cc. We build the _cc version and derive the _hist from that.
2. Select all polygons (or unselect all) and build the mesh using Feature Objects -> Map to 2D Mesh. We do not usually include the suffix "_Mesh" in our names. Name it with the exact name and lower case used for the map. This will not cause significant confusion.
3. Make sure that the mesh relaxation options follow our standard. Select the mesh to enable the mesh module, which will change the menu at the top. Choose "Elements" and "Options" and make sure Interior Element Relax number of iterations is set to 200 and "Area Relax".
4. Back in the maps, select the mesh_relax_selections coverage. This may be generically named, or it may have a version number that matches the map version number. 
5. Select the polygon tool and then select all polygons (selecting one and typing control-A will do this).
6. Use the polygons you just selected to select elements in the mesh. To do this choose Feature Objects -> Select/Delete Data. Set the selectable object to "mesh" and "elements" and point to the mesh you created. 
7. Right click and choose "relax"
8. Repeat the selection step 6 using "mesh_merge_selections" as the set of polygons to guide selection. This time, instead of relaxing as in step 7. choose "merge triangles on the last step.
9. Repeat steps 6-7 one more time. The merging can cause skew elements that must be relaxed a second time.
10. Duplicate the _cc mesh to _hist. 
11. Select the _hist mesh. Use the polygon selection tool and the prune_to_hist coverage to select all the *nodes* (not elements this time) that are in the cc mesh but not in hist. Delete them.
12. Select post_prune coverage, go back to selecting elements and smooth the hist mesh one more time. This increases element sizes in the Tule Red area of Yolo.
13. For both _hist and _cc, select "renumber seed" coverage. Right click it and "zoom to the coverage".
14. Select the mesh to enable the mesh module. Select the (only) mesh node that is inside the polygon. 
15. Under "nodes" in the mesh module, select "Renumber". 
16. Save your work.

 