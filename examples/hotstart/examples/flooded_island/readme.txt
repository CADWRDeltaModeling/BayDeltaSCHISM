flooded_island
This test case initiated hotstart from a baseline run. 
The model grid for the baseline run is slightly different from the current run in that the current run includes an additional island, Johnes.
For water level initialization, 'patch_init' is applied. 
For the region 'jone', water level is set just 0.1 meter below the bottom. In SCHISM, if the initial water level is set way below the bottom of the island to be flooded, the water will seep into the ground first before filling up the island. 
For the rest of the region 'bay-delta', water level from the baseline run is applied. 
Note that for 'patch_init', allow_overlap is set to True. This is because 'bay_delta' region, which covers the entire computational domain, and 'jones', which only includes the flooded island, are overlapping. Overlapping between the two regions is by default not allowed (allow_overlap=False by default). However, when allow_overlap=True and overlapping region exists, the overlapping region is assigned to the last defined region that includes the shared region in hotstart.yaml file. For instance, in the example case, although both 'bay_delta' and 'jones' covers Johes island, this region is assigned to 'jones' region because it is defined later in the yaml file. 
An example shapefile for the test case is in shapefile\
For an ihot=2 continuation, keep run_start at the original simulation origin and set date to the restart moment. Schimpy computes time, iths, and nsteps_from_cold from those values and time_step; do not patch the generated clock variables manually.