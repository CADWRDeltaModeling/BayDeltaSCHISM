.. _bds_guide_azure:

=========================================
Step-by-step: Bay-Delta SCHISM on Azure
=========================================

This guide will walk you through the process of setting up and running the Bay-Delta SCHISM model on Azure Batch. It could be helpful to first complete the Hello SCHISM tutorial on Azure :ref:`helloschism_azure`.

.. note::
    This assumes you have already `set up your Azure account <https://learn.microsoft.com/en-us/azure/batch/batch-account-create-portal>`_ and have access to the Azure Batch service. If you haven't done this yet, please refer to the Azure documentation for instructions on how to create an account and set up Batch.

.. warning::

    This documentation is provided solely as guidance for using Azure Batch with SCHISM and related tools. The authors and organizations involved are not affiliated with, endorsed by, or in partnership with Microsoft Azure. No promotion or recommendation of Azure services is intended; Azure is referenced here only because it is the platform currently used for these workflows by DWR's Modeling Support Office.

.. warning::

    The documentation and support from DWR's Modeling Support Office is limited to the most current Bay Delta SCHISM model and it's inputs. We do not offer general SCHISM support.

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
