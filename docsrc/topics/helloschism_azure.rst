.. _helloschism_azure:

=========================================
Step-by-step: HelloSCHISM on Azure
=========================================

This guide will walk you through the process of running the tutorial HelloSCHISM model on Azure Batch.

.. note::
    This assumes you have already `set up your Azure account <https://learn.microsoft.com/en-us/azure/batch/batch-account-create-portal>`_ and have access to the Azure Batch service. If you haven't done this yet, please refer to the Azure documentation for instructions on how to create an account and set up Batch.

.. warning::

    This documentation is provided solely as guidance for using Azure Batch with SCHISM and related tools. The authors and organizations involved are not affiliated with, endorsed by, or in partnership with Microsoft Azure. No promotion or recommendation of Azure services is intended; Azure is referenced here only because it is the platform currently used for these workflows by DWR's Modeling Support Office.

Initial Setup
--------------

First, complete the Azure setup steps in :ref:`setup_azure`. You should have:

* azure_cli and azcopy command line utilities installed and configured
    * meaning you can run `azcopy` and `az` commands from the command line
    * you should be logged into your azure account
* download and install azure_dms_batch and its conda environment
* upload the necessary packages and libraries to your Azure batch account (see :ref:`azure_upload_apps`)


Uploading Model Input Files
-------------------------------

Your simulation input files (e.g., mesh, forcing files, etc.) should be uploaded to the Azure Batch storage account. This is typically done using the `azcopy` command line utility. The :ref:`azcopy_info` section has basic info on azcopy commands. 

For more detailed info see the `Microsoft documentation <https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10?toc=%2Fazure%2Fstorage%2Fblobs%2Ftoc.json&bc=%2Fazure%2Fstorage%2Fblobs%2Fbreadcrumb%2Ftoc.json&tabs=dnf>`_.

#. Navigate to "./modules/**m1_hello_schism**" in a terminal (PowerShell, Bash, etc.) and activate your azure_dms_batch conda environment.
    ex: 

    .. code-block:: console

        cd ./modules/m1_hello_schism
        conda activate azure

#. Make sure that there is an **/outputs** directory inside the module directory. We include this with the module folder, so it should be there.

#. Create a blob container within your storage account. You can use the console variables as described in :ref:`console_vars` or just replace the values in the command below with your own.

    .. code-block:: console

        az storage container create --name modules --account-name $MY_STORAGE --auth-mode login

#. Now you'll need to generate an SAS token in order to read/write/copy/etc. to and from your storage account's blob container "modules". See :ref:`azuresas` for more info on this process, but copy the Blob url link for the next step.

#. Specify the sas variable using the url you generate in :ref:`azuresas`
    .. code-block:: console

        export sas="<url.link.here>"

    Be sure to include the quotation marks.

#. Set the AZLINK variable using this formula:

    ``https://<storage account name>.blob.core.windows.net/<blob container name>/``

    .. code-block:: console

        export AZLINK="https://<storage account name>.blob.core.windows.net/modules/"

    Replace <storage account name> with the name of your storage account. And the blob container name is "modules" as specified in step 4.

#. Now you can copy the contents of the module 1 folder into your blob container using `azcopy`. First, keep the **--dry-run** flag on so you can be *sure* that your files are going where you want them to go.

    .. code-block:: console

        azcopy copy "./" "${AZLINK}?${sas}" --exclude-regex="outputs/.*" --recursive --preserve-symlinks --dry-run

    Once you've checked the console output and are sure it's going to and from the right place, you can re-run it without the --dry-run flag.

    This will copy all the files in m1_hello_schism into the modules blob container. It will also *not* upload any of the files in the `outputs` folder (because of the ``--exclude-regex='outputs/.*'``). This is a good practice so you don't incur extra costs for uploading and downloading large output \*.nc files.

Check that your files were uploaded correctly by navigating to your storage account with either the online `Azure Portal <https://portal.azure.com/>`_ or `the Azure Storage Explorer (desktop app) <https://azure.microsoft.com/en-us/features/storage-explorer/#overview>`_. 

You should be able to see your `m1_hello_schism folder` and it's contents inside of the `modules` blob container.

Set up Model Run Config
-------------------------

You can use the **azure_dms_batch** package's command line utilities to submit a job to Azure.

Much of the setup for the virtual machines, compute nodes, etc. are determined by which template you specify in your run \*.yml file.

But First,you'll need to modify HelloSCHISM/azure_yml_files/m1_hello_schism_run.yml:

* resource_group: fill in the name of your Azure Resource Group
* batch_account_name: fill in your Batch Account name
* storage_account_name: fill in your Storage Account name
* location: **(at the bottom)**, if your Azure resources were created in a location other than "eastus" then you'll need to specify the location here.

Some important things to note: 

The run_file.yml overrides anything in your default_config.yml (ex: `alma87_mvapich2_20241018/default_config.yml <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/dmsbatch/templates/alma87_mvapich2_20241018/default_config.yml>`_)

Spot Pricing Config
::::::::::::::::::::

The above example uses "Low Priority Nodes" or "`spot pricing <https://learn.microsoft.com/en-us/azure/batch/batch-spot-vms>`_". You can see this by ``TargetDedicatedNodes`` in the m1_hello_schism_run.yml file. 

Spot pricing works by sending your job to Spot VMs which run until there is another process that preempts your job. So this will take longer but can be much more affordable if you're running many simulations. For HelloSCHISM you can change this to "TargetDedicatedNodes"

This means your job needs the capacity to automatically restart from the last hotstart produced by SCHISM.

This `example schism.yml file uses spot pricing <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/sample_configs/sample_schism_spot_pricing.yml>`.

This `example schism.yml file uses dedicated nodes <https://github.com/CADWRDeltaModeling/azure_dms_batch/blob/main/sample_configs/sample_schism.yml>`. The example yml file has many comments on each input with explanations.


Run Simulation!
---------------

.. note::
    Make sure you have machine quota as specified in :ref:`batch_quota` before submitting a job.

Navigate to HelloSCHISM/azure_yml_files in the console.

To submit a run you just need to enter the following command in a console which you have **azure_cli**, **azcopy**, and **azure_dms_batch** activated and which you're logged into (likely using the `azure` conda environment you created earlier).

    .. code-block:: console

        dmsbatch schism submit-job --file m1_hello_schism_run.yml