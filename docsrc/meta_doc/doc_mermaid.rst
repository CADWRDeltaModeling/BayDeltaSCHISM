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

.. code-block:: RST

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

.. _cool_mermaid:

Cool stuff
----------

Clickables
````````````

You can make elements clickable with something simple like: 

.. mermaid::

   graph LR
      clickable["Click Me"]
      click clickable "https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/meta_doc/doc_mermaid.html#cool-stuff" _blank
      clickable --> notclick(["Don't Click Me"])

The chart above was made with the in-line capabilites of the sphinxcontrib.mermaid extension, which looks like the following text inside an .rst file:

.. code-block:: RST

    graph LR
      clickable["Click Me"]
      click clickable "https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/meta_doc/doc_mermaid.html#cool-stuff" _blank
      clickable --> notclick(["Don't Click Me"])

But that has it's limitations, and doesn't always render well. So a simple .mmd version of the above chart would be: 

.. code-block:: RST

    flowchart TD

        clickable["Click Me"]
        click clickable "https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/meta_doc/doc_mermaid.html#cool-stuff" _blank
        clickable --> notclick(["Don't Click Me"])

Icons in an Element 
```````````````````````

You can add icons within your node, there's a library here: https://icones.js.org/

You can search for whatever you want, let's say we want a cactus! You can select the icon that speaks to you and then scroll to the bottom and click the Links \> URL button to copy the link to the icon you want.

.. mermaid::

   graph LR
      color_cactus[<span style='display: inline-flex; align-items: center;'><img src='https://api.iconify.design/emojione:cactus.svg' width='20' height='20' style='margin-right: 4px;' /> Colorful Cactus</span>]

      white_cactus[<span style='display: inline-flex; align-items: center;'><img src='https://api.iconify.design/tabler:cactus.svg?color=white' width='20' height='20' style='margin-right: 4px;' /> White Cactus</span>]
      
      blue_cactus[<span style='display: inline-flex; align-items: center;'><img src='https://api.iconify.design/tabler:cactus.svg?color=blue' width='20' height='20' style='margin-right: 4px;' /> Blue Cactus</span>]

      color_cactus --> white_cactus --> blue_cactus

From the code below you can see that you can change the color of an icon by adding `?color=white` to the end of the img src="" url.