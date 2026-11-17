.. _documentation:

==================================
Contributing to the Documentation
==================================

Introduction
-------------  

We use the python-based html documentation generator package `Sphinx <https://www.sphinx-doc.org/en/master/>`_ to create our webpage (including this one!). It uses `reStructuredText (.rst) <https://docutils.sourceforge.io/rst.html>`_ which is a component of yet another python package `Docutils <https://docutils.sourceforge.io/index.html>`_. The reStructuredText files are written in an easy-to-read lightweight markup language. You can see how this very webpage looks in reStructuredText by looking at the source file in the GitHub repository: `docsrc/documentation.rst <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/docsrc/documentation.rst>`_

We also use a diagram visualization tool `Mermaid <https://mermaid.js.org/intro/>`_ which uses JavaScript to render Markdown-inspired text into beautiful flowcharts and diagrams.

And last but certainly not least, we use `Click <https://click.palletsprojects.com/en/stable/>`_ to create command line interfaces (cli) for our code. Sphinx has a plugin `sphinx-click <https://sphinx-click.readthedocs.io/en/latest/>`_ which allows for automatic documentation for our cli commands.


Getting Started
----------------
.. _bds_doc:

The documentation environment is the SCHISM runtime environment in
`schism_env.yml <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/main/schism_env.yml>`_
plus a documentation overlay, ``environment-doc.yml``, that adds Sphinx and its extensions.
Both files are in the root of the BayDeltaSCHISM repository.

First, clone the repository using::

    git clone https://github.com/CADWRDeltaModeling/BayDeltaSCHISM.git

Then open a terminal that has conda enabled (PowerShell, Anaconda prompt, etc) in your BayDeltaSCHISM folder.

Windows
=========

Run the helper script::

    .\build_doc_env.bat

Linux and macOS
===============

Run the helper script::

    bash build_doc_env.sh

What the helper does
====================

The helper creates a conda environment called ``bds_doc`` from ``schism_env.yml``, updates it with
``environment-doc.yml``, and installs your checkout of ``bdschism`` in editable mode. It refuses to
replace an existing ``bds_doc`` environment, does not build the pages, and does not leave your terminal
activated. Run ``build_doc_env.bat --help`` (or ``bash build_doc_env.sh --help``) for details.

If you prefer, perform the same steps yourself::

    conda env create -n bds_doc -f schism_env.yml
    conda env update -n bds_doc -f environment-doc.yml
    conda activate bds_doc
    python -m pip install --no-deps --no-build-isolation -e ./bdschism

Do not add ``--prune`` to the update step: the overlay lists only the documentation tools, so pruning
would remove the SCHISM runtime packages. If ``bds_doc`` already exists and is compatible, run only the
update step rather than deleting it.

The overlay requires Sphinx 8.2 or later (within the 8.x series), which provides the ``sphinx.ext.apidoc``
extension that generates the API pages. Rendering Mermaid diagrams in the HTML pages does not require a
separate Mermaid installation.

To activate the environment, simply type::

    conda activate bds_doc

How it works
-------------

Local html pages
================

Before you even start modifying or adding documentation, try activating the environment you made in :ref:`Getting Started <bds_doc>`. Then all you need to do to be able to test the documentation is navigate to BayDeltaSCHISM/docsrc and type::

    make html

On Windows PowerShell, use ``.\make.bat html``. For a clean rebuild, run ``make clean`` followed by ``make html``.

This will generate all of the necessary html files in order to render the webpage that is eventually hosted on GitHub (`here <https://cadwrdeltamodeling.github.io/BayDeltaSCHISM>`_). But any html files that you render locally (by running ``make html``) are just for you to see and check. You do not *need* to run ``make html`` for any of your changes to the `.rst` files to regenerate the GitHub webpage, but it's highly recommended in order to review your changes and make sure they're behaving as expected once rendered on GitHub.

The home page is always ``docs/html/index.html``. If you open that in your browser you can navigate a local version of the webpage and test the functionality of the .rst file edits you made. The generated ``docs/`` folder is not tracked by git.

The API reference for the ``bdschism`` Python package is generated from the source code as part of every build (by ``sphinx.ext.apidoc``, configured in ``docsrc/conf.py``) into ``docsrc/_api/``, which is also not tracked. You do not need to run a separate command after adding a module, and you should not edit or commit the generated files. The page ``docsrc/bdschism.rst`` only links to the generated package page. A successful build does not by itself show that every module was documented: check the build messages for failed imports and look at the API pages.


GitHub Pages
==============

Whenever a commit is pushed to the default branch of the `BayDeltaSCHISM <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM>`_ repository (or a version tag is pushed), a `GitHub Action <https://github.com/features/actions>`_ renders the .rst files using Sphinx and publishes them. This action's process is defined using the `.github/workflows/build_sphinx.yml <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/main/.github/workflows/build_sphinx.yml>`_ workflow document. You can tell that it's triggered by the "on" section of the yaml file:

    .. code-block:: yaml
        :emphasize-lines: 3, 4, 5, 6

        name: "Sphinx: Render docs"

        on: 
            # Runs on pushes targeting the default branch
            push:
            branches: ["main"]

        ...

The workflow has two jobs. The build job creates the same environment as the local process for :ref:`Getting Started <bds_doc>` (``schism_env.yml`` plus ``environment-doc.yml``, with your checkout installed), runs ``make clean`` and ``make html``, and uploads ``docs/html`` as a Pages artifact. The separate deploy job publishes that artifact to the `BayDeltaSCHISM website <https://cadwrdeltamodeling.github.io/BayDeltaSCHISM>`_. Only a successful build can start the deployment, and a successful build does not guarantee that deployment succeeded, so check both jobs in the **Actions** tab.

In the repository **Settings -> Pages -> Build and deployment**, the source must be **GitHub Actions**; there is no branch or folder to select. The ``github-pages`` environment (**Settings -> Environments**) must allow the branch or tag that is being published. The older ``gh-pages`` branch is not used by this workflow. Do not commit the generated site.


Examples and Concepts
------------------------------

.. toctree::
  :maxdepth: 4
  :titlesonly:
  
  meta_doc/doc_sphinx.rst
  meta_doc/doc_mermaid.rst
  meta_doc/doc_click.rst