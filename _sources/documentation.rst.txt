.. _documentation:

================================
Documentation of BayDeltaSCHISM
================================

Introduction
-------------  

We use the python-based html documentation generator package `Sphinx <https://www.sphinx-doc.org/en/master/>`_ to create our webpage (including this one!). It uses `reStructuredText (.rst) <https://docutils.sourceforge.io/rst.html>`_ which is a component of yet another python package `Docutils <https://docutils.sourceforge.io/index.html>`_. The reStructuredText files are written in an easy-to-read lightweight markup language. You can see how this very webpage looks in reStructuredText by looking at the source file in the GitHub repository: `docsrc/documentation.rst <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/docsrc/documentation.rst>`_

We also use a diagram visualization tool `Mermaid <https://mermaid.js.org/intro/>`_ which uses JavaScript to render Markdown-inspired text into beautiful flowcharts and diagrams.

And last but certainly not least, we use `Click <https://click.palletsprojects.com/en/stable/>`_ to create command line interfaces (cli) for our code. Sphinx has a plugin `sphinx-click <https://sphinx-click.readthedocs.io/en/latest/>`_ which allows for automatic documentation for our cli commands.


Getting Started
----------------
.. _bds_doc:

Windows
=========

There's a batch script in the BayDeltaSCHISM repository that you can use to set up your conda environment that's compatible with our documentation utilities.

First, clone the repository using::

    git clone https://github.com/CADWRDeltaModeling/BayDeltaSCHISM.git

Then open a terminal that has conda enabled (PowerShell, Anaconda prompt, etc) and navigate to your BayDeltaSCHISM folder and type::

    ./setup_doc_env_windows.bat

This will create a conda enviornment called "bds_doc" using `BayDeltaSCHISM/schism_env.yml <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/schism_env.yml>`_, and then download a utility for generating Mermaid diagrams, and finally install the documentation dependencies of bdschism.

To activate the environment, simply type::

    conda activate bds_doc

Linux
=====

Guidance for Linux has yet to be documented.

How it works
-------------

Local html pages
================

Before you even start modifying or adding documentation, try activating the environment you made in :ref:`Getting Started <bds_doc>`. Then all you need to do to be able to test the documentation is navigate to BayDeltaSCHISM/docsrc and type::

    make html

This will generate all of the necessary html files in order to render the webpage that is eventually hosted on GitHub (`here <https://cadwrdeltamodeling.github.io/BayDeltaSCHISM>`_). But any html files that you render locally (by running ``make html``) are just for you to see and check. You do not *need* to run ``make html`` for any of your changes to the `.rst` files to regenerate the GitHub webpage, but it's highly recommended in order to review your changes and make sure they're behaving as expected once rendered on GitHub.

The home page is always ``docs/index.html``. If you open that in your browser you can navigate a local version of the webpage and test the functionality of the .rst file edits you made.


GitHub Pages
==============

Whenever a commit is pushed to the `BayDeltaSCHISM <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM>`_ repository, a few `GitHub Actions <https://github.com/features/actions>`_ are automatically triggered.

The first is to render the .rst files using Sphinx and save to the `gh-pages branch of the repository <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/gh-pages>`_. This action's process is defined using the `.github/workflows/build_sphinx.yml <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/.github/workflows/build_sphinx.yml>`_ workflow document. You can tell that it's triggered by the "on" section of the yaml file:

    .. code-block:: yaml
        :emphasize-lines: 3, 4, 5, 6

        name: "Sphinx: Render docs"

        on: 
            # Runs on pushes targeting the default branch
            push:
            branches: ["main", "master"]

        ...

The rest of the file creates an environment (similar to the local process for :ref:`Getting Started <bds_doc>`), then runs ``make clean`` and ``make html``, then pushes those html changes to the `gh-pages branch of the repository <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/tree/gh-pages>`_.

From there, a new action is triggered because the gh-pages page has been pushed to, and there's a `GitHub-configured action <https://github.com/marketplace/actions/deploy-to-github-pages>`_ that then takes the `index.html <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/gh-pages/index.html>`_ file and hosts it on our `BayDeltaSCHISM website <https://cadwrdeltamodeling.github.io/BayDeltaSCHISM>`_.


Further Documentation Concepts
------------------------------

.. toctree::
  :maxdepth: 4
  :titlesonly:
  
  meta_doc/doc_sphinx.rst
  meta_doc/doc_mermaid.rst
  meta_doc/doc_click.rst
  meta_doc/doc_examples.rst