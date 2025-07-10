.. _azure:

================================================
Running on Azure Batch
================================================

Azure Batch is a cloud-based service that allows you to run large-scale parallel and high-performance computing applications. This section provides an overview of how to set up and run SCHISM on Azure Batch.

.. _setup_azure:

Setup Azure 
---------------------

Download Azure Utilities
``````````````````````````````

Azure is a paid service separate from SCHISM, BayDeltaSCHISM, and CA-DWR. Once you have set up your Azure batch and storage accounts within your Azure resource group, you'll need to download a few things:

* `Azure CLI <https://learn.microsoft.com/en-us/cli/azure/?view=azure-cli-latest>`_
    * download and install on your machine to pass jobs (simulations) to Azure batch
    * this is likely a command line string that you'll run and re-launch a terminal
* `AzCopy <https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10?tabs=dnf>`_
    * download and install on your machine to upload content to storage container
* `Azure Batch Explorer (desktop app) <https://azure.github.io/BatchExplorer/>`_
    * this isn't technically necessary, but is quite helpful in managing ongoing simulations
* `Azure Storage Explorer (desktop app) <https://azure.microsoft.com/en-us/features/storage-explorer/#overview>`_
    * again, not technically necessary, but quite useful

Setup can be done via az commands. Here we setup a batch account with associated storage.

Login
````````````````

Login with your Azure credentials in a console with admin access. 
    
    .. code-block:: console

        az login --use-device-code

Copy in the code from the console then go to https://microsoft.com/devicelogin and paste into the browser window to verify your credentials.

You may get a "certificate verify failed" message. If you are on a government network you may have firewall settings that restrict all SSL. You'll either need to talk to your IT personell or use a personal network.

To test that your login worked, use:

    .. code-block:: console

        az account show

This will show your account info.

Create a Resource Group
``````````````````````````

See the Azure docs for details. To use the commands below, enter your values (replacing the <angle brackets and values>)

    .. code-block:: console

        az group create --name <resource_group_name> --location <location_name>

        az storage account create --resource-group <resource_group_name> --name <storage_account_name> --location <location_name> --sku Standard_LRS

        az batch account create --name <batch_account_name> --storage-account <storage_account_name> --resource-group <resource_group_name> --location <location_name>

For the --location, you can use any location, but eastus and eastus2 is what DWR uses. The storage account name typically ends in "sa", and the batch account typically ends in "batch" for ease of navigating resources on Azure.

You can also create the batch account and associated account as `explained here <https://docs.microsoft.com/en-us/azure/batch/batch-account-create-portal>`_.

You may encounter some errors about regional quotas. You'll want your resource group, storage account, and batch account in the same region/location.


Download azure_dms_batch
````````````````````````````

**Git clone *this* project**

    .. code-block:: console

        git clone https://github.com/CADWRDeltaModeling/azure_dms_batch.git

Navigate to the azure_dms_batch folder created above, and use the environment.yml with conda to create an environment called azure

    .. code-block:: console

        conda env create -f environment.yml

or *if you're not using conda*:

    .. code-block:: console

        pip install -r requirements.txt


Stay in the azure_dms_batch repo folder and then install using:

    .. code-block:: console

        conda activate azure
        pip install --no-deps -e .

For more information on the azure_dms_batch package, see the `README.md <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/README.md>`_ file.


Upload Applications
---------------------

Azure batch requires the setup and installation to happen via zip files that are called application packages. The user should specify these packages with the version names as specified in the template. Here we will refer to the `alma87_mvapich2 template <https://github.com/CADWRDeltaModeling/azure_dms_batch/tree/main/dmsbatch/templates/alma87_mvapich2_20241018>`_.

The `app-packages/batch_app_package_and_upload.sh <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/app-packages/batch_app_package_and_upload.sh>`_ script can be used to upload the packages which you will do in the following steps.

SCHISM
`````````

For SCHISM, you'll need to either compile and zip the executables yourself, or you can refer to `the releases page <https://github.com/CADWRDeltaModeling/azure_dms_batch/releases>`_ and download the relevant **\schism_with_deps_\*.zip** file. For HelloSCHISM and BayDeltaSCHISM tutorials, we'll refer to `the latest schism release, schism_with_deps_5.11.1_alma8.7hpc_v4_mvapich2.zip <https://github.com/CADWRDeltaModeling/azure_dms_batch/releases/download/schism_5.11_alma8.7/schism_with_deps_5.11.1_alma8.7hpc_v4_mvapich2.zip>`_. You'll also need `the latest alma release, nfs_alma8.7 <https://github.com/CADWRDeltaModeling/azure_dms_batch/releases/download/schism_5.11_alma8.7/nfs_alma8.7.zip>`_.

Save the .zip file to your local azure_dms_batch repository under azure_dms_batch/app-packages.

Now use `app-packages/batch_app_package_and_upload.sh <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/app-packages/batch_app_package_and_upload.sh>`_ to upload in the command line:

    .. code-block:: console

        export MY_BATCH_ACCOUNT="<batchaccountname>"
        export MY_RG="<resourcegroupname>"

        cd azure_dms_batch/app-packages

        source batch_app_package_and_upload.sh
        
        package_and_upload_telegraf "telegraf" $MY_BATCH_ACCOUNT $MY_RG
        package_and_upload_app schism_with_deps 5.11.1_alma8.7hpc_v4_mvapich2 schism_with_deps_5.11.1_alma8.7hpc_v4_mvapich2.zip  $MY_BATCH_ACCOUNT $MY_RG
        package_and_upload_app nfs_alma 8.7 nfs_alma8.7.zip  $MY_BATCH_ACCOUNT $MY_RG
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

You can check the versions of packages and which is considered the default by going to the online `Azure Portal <https://portal.azure.com/>`_ and navigating to your batch account. Once in your batch account, navigate to Features \> Applications. There you'll see th application IDs as well as the default version that's being used.

If you were to want to upload a development or updated version of any of these packages you could use a similar approach to the package_and_upload techniques, and then use the online portal to specify the default version.


References
-----------

`Python SDK Setup <https://docs.microsoft.com/en-us/azure/developer/python/azure-sdk-overview>`_
`BlobStorage Python Example <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-blob>`_
`Azure Batch Python API <https://docs.microsoft.com/en-us/python/api/overview/azure/batch?view=azure-python>`_
`Azure Batch Python Samples <https://github.com/Azure-Samples/azure-batch-samples/tree/master/Python>`_
`Azure Batch Shipyard <https://github.com/Azure/batch-shipyard>`_

MPI specific
`Azure Batch MPI <https://docs.microsoft.com/en-us/azure/batch/batch-mpi>`_
`Cluster configuration options <https://docs.microsoft.com/en-us/azure/virtual-machines/sizes-hpc#cluster-configuration-options>`_

Intel MPI
`Azure settings for Intel MPI <https://docs.microsoft.com/en-us/azure/virtual-machines/workloads/hpc/setup-mpi#intel-mpi>`_
`Intel MPI Pre-requisites <https://www.intel.com/content/www/us/en/develop/documentation/mpi-developer-guide-linux/top/installation-and-prerequisites/prerequisite-steps.html>`_
