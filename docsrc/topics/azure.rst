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
* `AzCopy <https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10?tabs=dnf>`_
    * download and install on your machine to upload content to storage container
* `Azure Batch Explorer (desktop app) <https://azure.github.io/BatchExplorer/>`_
    * this isn't technically necessary, but is quite helpful in managing ongoing simulations
* `Azure Storage Explorer (desktop app) <https://azure.microsoft.com/en-us/features/storage-explorer/#overview>`_
    * again, not technically necessary, but quite useful

Setup can be done via az commands. Here we setup a batch account with associated storage.

Login
````````````````

Login with your Azure credentials. First go to https://microsoft.com/devicelogin and copy your login code. Then after typing:
    
    .. code-block:: console

        az login --use-device-code

Copy in the code to verify your credentials.

Create a Resource Group
``````````````````````````

See the Azure docs for details. To use the commands below, enter your values (replacing the <angle brackets and values>)

    .. code-block:: console

        az group create --name <resource_group_name> --location <location_name>

        az storage account create --resource-group <resource_group_name> --name <storage_account_name> --location <location_name> --sku Standard_LRS

        az batch account create --name <batch_account_name> --storage-account <storage_account_name> --resource-group <resource_group_name> --location <location_name>

You can also create the batch account and associated account as `explained here <https://docs.microsoft.com/en-us/azure/batch/batch-account-create-portal>`_.


Download azure_dms_batch
````````````````````````````

Use the environment.yml with conda to create an environment called azure
    .. code-block:: console

        conda env create -f environment.yml

or

    .. code-block:: console

        pip install -r requirements.txt

**Git clone *this* project**

    .. code-block:: console

        git clone https://github.com/CADWRDeltaModeling/azure_dms_batch.git

Change directory to the location of the azure_dms_batch project and then install using:

    .. code-block:: console

        pip install --no-deps -e .

For more information on the azure_dms_batch package, see the `README.md <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/README.md>`_ file.

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
