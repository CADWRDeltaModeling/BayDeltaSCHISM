.. _problems:

#############################
Common Problems and Diagnosis
#############################

At the bottom of this page you'll find tables of common SCHISM error messages and their solutions. 

If you encounter an error message that is not listed, please report it to the developers with the error message and any relevant details about your run (e.g., input files, command used to run, etc.). This will help us improve the documentation and assist other users who may encounter the same issue in the future. Or if you're comfortable editing the documentation, you can add the error message and solution to the appropriate table yourself. See the :ref:`Contributing <bds_doc>` section for more details on how to contribute to the documentation.

Where does SCHISM write error messages?
---------------------------------------

If SCHISM is running and encounters an error, it will write the error message to the `outputs/fatal.error` file. If this file has any content, then you can guarantee the run has failed.

At times you'll get errors in the job submission system (e.g., SLURM) that are not written to the `fatal.error` file. In this case, you can check the job's standard output and error files for any messages.

Common Problems
----------------------

SIGSEGV or segmentation fault
``````````````````````````````

This can be due to low disk space or insufficient memory. On linux use `ulimit -s unlimited` to allow for unlimited stack size. If the problem persists, check the `fatal.error` file for more details.

The runs seems very slow compared to normal
````````````````````````````````````````````



Dry boundary
`````````````

Dry boundary will appear in the `fatal.error` file and will say something along the lines of "ABORT:  STEP: wetted cross section length on open bnd". 

This most often appears in Clifton Court and in the Yolo Toedrain boundaries. The issue is when the boundary is trying to take water out of the system (positive value) and it cannot because of insufficent water available in the boundary cell. Most boundaries are artificially deepened to avoid this, but the error can occur when running a non-historic/hindcast simulation and the Yolo Toedrain boundary is trying to replicate the tidal boundary in the wrong timing with the rest of the system. Similarly if the Clifton Court SWP allocated diversion is out of sync with the water levels in the system you'll need to run the `ccf_gate utility in bdschism <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/bdschism/bdschism/ccf_gate_height.py>`_ to properly adjust the timing of the gates. 

SCHISM Errors & Solutions
--------------------------

.. xlsx-table:: SCHISM Error Messages and Solutions
   :file: ../tables/schism_error_solutions.xlsx
   :header-rows: 1
   
SCHISM Utility Errors & Solutions
----------------------------------

.. xlsx-table:: SCHISM Utility Error Messages and Solutions
   :file: ../tables/schism_utility_errors_solutions.xlsx
   :header-rows: 1