.. _bds_guide_azure:

=========================================
Step-by-step: Bay-Delta SCHISM on Azure
=========================================

This guide will walk you through the process of setting up and running the Bay-Delta SCHISM model on Azure Batch.

.. note::
    This assumes you have already `set up your Azure account <https://learn.microsoft.com/en-us/azure/batch/batch-account-create-portal>`_ and have access to the Azure Batch service. If you haven't done this yet, please refer to the Azure documentation for instructions on how to create an account and set up Batch.

Initial Setup
--------------

First, complete the Azure setup steps in :ref:`setup_azure`. You should have:

* azure_cli and azcopy command line utilities installed and configured
    * meaning you can run `azcopy` and `az` commands from the command line
    * you should be logged into your azure account
* download and install azure_dms_batch and its conda environment

Upload Applications
---------------------

Azure batch requires the setup and installation to happen via zip files that are called application packages. The user should specify these packages with the version names as specified in the template. Here we will refer to the `alma87_mvapich2 template <https://github.com/CADWRDeltaModeling/azure_dms_batch/tree/main/dmsbatch/templates/alma87_mvapich2_20241018>`_.

The `app-packages/batch_app_package_and_upload.sh <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/app-packages/batch_app_package_and_upload.sh>`_ script can be used to upload the packages. 

SCHISM
`````````

For SCHISM, you'll need to either compile and zip the executables yourself, or you can refer to `the releases page <https://github.com/CADWRDeltaModeling/azure_dms_batch/releases>`_ and download the relevant **\schism_with_deps_\*.zip** file.

Save the .zip file to azure_dms_batch/app-packages.

Now use `app-packages/batch_app_package_and_upload.sh <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/app-packages/batch_app_package_and_upload.sh>`_ to upload in the command line:

    .. code-block:: console

        export MY_BATCH_ACCOUNT="<batchaccountname>"
        export MY_RG="<resourcegroupname>"

        cd azure_dms_batch/app-packages

        source batch_app_package_and_upload.sh
        
        package_and_upload_telegraf "telegraf" $MY_BATCH_ACCOUNT $MY_RG
        package_and_upload_app schism_with_deps 5.11.1_alma8.7hpc_v4_mvapich2 schism_with_deps_5.11.1_alma8.7hpc_v4_mvapich2.zip  $MY_BATCH_ACCOUNT $MY_RG
        package_and_upload_app nfs_alma8.7 nfs_alma8.7.zip  $MY_BATCH_ACCOUNT $MY_RG
        package_and_upload_batch_setup "../schism_scripts/" $MY_BATCH_ACCOUNT $MY_RG

Python Packages
```````````````

For python packages like schimpy and BayDeltaSCHISM's bdschism you can also use the **batch_app_package_and_upload.sh** script to upload the packages to your batch account.


    .. code-block:: console

        export MY_BATCH_ACCOUNT="<batchaccountname>"
        export MY_RG="<resourcegroupname>"

        cd azure_dms_batch/app-packages

        source batch_app_package_and_upload.sh

        package_and_upload_schimpy $MY_BATCH_ACCOUNT $MY_RG
        package_and_upload_bdschism $MY_BATCH_ACCOUNT $MY_RG

The above utility names the package with *today's date* and then uploads it and sets it to the default version.

You can check the versions of packages and which is considered the default by going to the online `Azure Portal <https://portal.azure.com/>`_ and navigating to your batch account. ONce in your batch account, navigate to Features \> Applications.

Uploading Model Input Files
-------------------------------

Your simulation input files (e.g., mesh, forcing files, etc.) should be uploaded to the Azure Batch storage account. This is typically done using the `azcopy` command line utility. For more detailed info see the `Microsoft documentation <https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10?toc=%2Fazure%2Fstorage%2Fblobs%2Ftoc.json&bc=%2Fazure%2Fstorage%2Fblobs%2Fbreadcrumb%2Ftoc.json&tabs=dnf>`_.

azcopy commands
````````````````

The basic syntax of azcopy to copy local to Azure is:

    .. code-block:: console

        azcopy copy "<local_directory>" "<azure_storage_account/blob_container>/?<sas_link>"

and for Azure to local:
    .. code-block:: console

        azcopy copy "<azure_storage_account/blob_container>/?<sas_link>" "<local_directory>"

But at the Delta Modeling Section we most often use something like:

    .. code-block:: console

        export AZLINK="https://<storage_account>.blob.core.windows.net/<blob_storage_container/"
        export sas="<sas_link>"

        azcopy copy "<local_directory>" "${AZLINK}<blob_storage_container>/?${sas}" --exclude-regex="outputs/.\*nc" --recursive --preserve-symlinks --dry-run

where:

* **local_directory** 
    * whatever local path to your simulation directory you're uploading
* **storage_account** 
    * name of your Storage Account through Azure (not the same as the Batch Account name)
* **blob_storage_container**
    * folder path to your blob storage container
    * this will look like a folder path (eg: project_name/simulations/)
* **sas_link** 
    * SAS permissions key (generated each day for security)
    * you can generate and copy this key by navigating to your storage account in the `Azure Portal <https://portal.azure.com/>`_ \> going to "Containers" \> find storage container \> right clicking \> Generate SAS \> Change "Permissions": click all boxes \> Click "Generate SAS token and URL"
    * copy the "Blob SAS token option"

azcopy options
```````````````
These are some of the most frequently used azcopy flag options:

* **--dry-run** 
    * this is useful to test your command before running
    * this flag prints a list of which files will be copied where without actually uploading/downloading anything
* **--recursive**
    * this will copy all files in all subdirectories
* **--preserve-symlinks**
    * any symbolic links will be preserved in the upload to the blob container
* **--include-regex**
    * use a Regular Expression to limit which files are included in the upload
    * ex: --include-regex="\suisun_\(2\|3\|7\)/.\*\;baseline_6/.\*\"
        * this would upload all folder contents of
            * suisun_2/
            * suisun_3/
            * suisun_7/
            * baseline_6/
        * The **.\*** string signifies "all contents"
* **--exclude-regex**
    * use a Regular Expression to determine which files are excluded in the upload
    * this is particularly useful for things like outputs \*.nc files and sflux \*.nc files which are very large and costly to upload
    * ex: --exclude-regex="outputs.\*/.\*nc;sflux/.\*nc"
        * this would exclude any files that end in "nc" that are found in the sflux, outputs, or outputs\* folders

Running Model Simulation
-------------------------

You can use the **azure_dms_batch** package's command line utilities to submit a job to Azure.

Much of the setup for the virtual machines, compute nodes, etc. are determined by which template you specify in your run \*.yml file.

Simple Run Config
```````````````````

Essentially, to fire a run you just need to submit the following command in a console which you have azure_cli, azcopy, and azure_dms_batch activated and which you're logged into:

    .. code-block:: console

        dmsbatch schism submit-job --file <path/to/sample_schism.yml>

An example of a SCHISM yaml file is `here <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/sample_configs/sample_schism.yml>`_. The example yml file has many comments on each input with explanations.

Some important things to note: 

The run_file.yml overrides anything in your default_config.yml (ex: `alma87_mvapich2_20241018/default_config.yml <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/dmsbatch/templates/alma87_mvapich2_20241018/default_config.yml>`_)

Spot Pricing Config
````````````````````

The above example uses "Dedicated Nodes". To save money (but perhaps take a bit longer time), you can use "Low Priority Nodes" or "`spot pricing <https://learn.microsoft.com/en-us/azure/batch/batch-spot-vms>`_". This works by sending your job to Spot VMs which run until there is another process that preempts your job. 

This means your job needs the capacity to automatically restart from the last hotstart produced by SCHISM.

This `example schism.yml file uses spot pricing <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/sample_configs/sample_schism_spot_pricing.yml>`.
