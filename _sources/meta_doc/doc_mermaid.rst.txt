.. _doc_mermaid:

Mermaid Chart Principles
=========================

The environment that you can create by following the :ref:`Getting Started <bds_doc>` section allows for you to generate standalone .svg files that you can then reference in .rst files.

BayDeltaSCHISM Standards
------------------------

Symbols
`````````

We follow the conventions of `Mermaid Syntax <https://mermaid.js.org/syntax/flowchart.html>`_ for the most part. But for process flows, files and decisions, we generally follow:

.. raw:: html
    :file: ../img/bds_mermaid_conventions.svg

The raw .mmd file for the above chart is in `docsrc/diagrams/bds_mermaid_conventions.mmd <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/docsrc/diagrams/bds_mermaid_conventions.mmd>`_

Style
```````

You can add the following pre-amble to your .mmd charts to use a consistent style across pages:

.. code-block:: md

    ---
    config:
    look: classic
    theme: base
    ---
    %%{
        init: {
            'theme': 'base',
            'themeVariables': {
            'primaryColor': '#fff',
            'primaryTextColor': '#000',
            'primaryBorderColor': '#002570',
            'lineColor': '#000',
            'secondaryColor': '#d1d1d1',
            'tertiaryColor': '#fff'
            }
        }
    }%%

This is found in `docsrc/diagrams/bds_style_template.mmd <https://github.com/CADWRDeltaModeling/BayDeltaSCHISM/blob/master/docsrc/diagrams/bds_style_template.mmd>`_


VS Code plugin
--------------

The easiest plugin to use with Mermaid charts is `Mermaid Chart <https://marketplace.visualstudio.com/items/?itemName=MermaidChart.vscode-mermaid-chart>`_ by mermaidchart.com

.. figure:: ../img/mermaid_chart_ext.png  
   :class: with-border  
   :width: 70%  
   :align: center  

   VS Code Mermaid Chart extension
   
This plugin allows you to preview your .mmd documents in another VS Code window.

Cool stuff
----------

You can make elements clickable 

EXAMPLE


You can add icons within your node

https://icones.js.org/

Copy Links/URL

Add style things by ?color=white