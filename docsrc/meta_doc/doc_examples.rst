.. _doc_examples:

Sphinx examples
================

Math
-----

You can use the ``.. math::`` directive to display mathematical equations using the ``sphinx.ext.mathjax`` extension (this is already configured in docsrc/conf.py). You can find a list of Greek letters and math symbols and how to display them in LaTeX `here <https://www.overleaf.com/learn/latex/List_of_Greek_letters_and_math_symbols>`_. Equations :eq:`eq_continuity` and `(2.12) <_eq_turb_closure>`_ are shown below with the following code. 

The reference to the first equation is done with ``:eq:`eq_continuity```. But since the second equation uses a custom tag number (to correspond to the `SCHISM 5.8 manual <https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwj_tMSBluKMAxXwDzQIHZAwKXMQFnoECBEQAQ&url=https%3A%2F%2Fccrm.vims.edu%2Fschismweb%2FSCHISM_v5.8-Manual.pdf&usg=AOvVaw270sBZoLrHtWj0RyZ_PdGa&opi=89978449>`_ equation numbers), you need to add a hyperlink target using ``.. _eq_turb_closure:`` and then reference it using ```(2.12) <_eq_turb_closure>`_``

.. code-block:: RST

    .. math::
        :label: eq_continuity

        \nabla \cdot u + \frac{\partial w}{\partial z} = 0

    .. _eq_turb_closure:
    .. math::

        \frac{Dk}{Dt} = \frac{\partial}{\partial z} \left(\nu_{k}^{\psi} \frac{\partial k}{\partial z}\right) + 
                        \nu M^2  + \kappa N^2 - \epsilon + c_{fk}\alpha|u|^3 \mathcal{H} (z_v-z) \tag{2.12}


.. math::
    :label: eq_continuity

    \nabla \cdot u + \frac{\partial w}{\partial z} = 0

.. _eq_turb_closure:
.. math::

    \frac{Dk}{Dt} = \frac{\partial}{\partial z} \left(\nu_{k}^{\psi} \frac{\partial k}{\partial z}\right) + 
                    \nu M^2  + \kappa N^2 - \epsilon + c_{fk}\alpha|u|^3 \mathcal{H} (z_v-z) \tag{2.12}



Figures
---------

You can embed figures using the ``..figure::`` directive. All figures (.png, .jpeg, .svg, etc) are stored in the **docsrc/img/** folder. When specifying the image file location it needs to be relative to the .rst file that is being used. So for this page, it is using the **docsrc/meta_doc/doc_examples.rst** file, so the references to a figure would be **../img/<FILENAME>**. 

To reference the figure, you can add a hyperlink above the figure and then reference it using ``:numref:`example_dwr_logo```. That would render as :numref:`example_dwr_logo`. You can embed a figure using the following code:

.. code-block:: RST

    .. _example_dwr_logo:  

    .. figure:: ../img/dwr_logo_small.png    
        :align: center  
        :width: 200px  
    
        A small California Department of Water Resources logo.

.. _example_dwr_logo:  

.. figure:: ../img/dwr_logo_small.png    
    :align: center  
    :width: 200px  
   
    A small California Department of Water Resources logo.

Diagrams
-----------

You can embed diagrams produced with Mermaid Charts as html using two methods. 

Sphinx Mermaid Directive
``````````````````````````

The first is to use the ``.. mermaid::`` directive directly in the ``.rst`` files. That would look something like:

.. code-block:: RST

    .. mermaid::
        :align: center

        flowchart LR
        
            id1(Box with round corner)
            id2([Stadium])
            id3[(Database)]
            id5{{Hex}}
            id6[\Parallelogram\]

            id1-->id2
            id1-->id3
            id2-.-id5

            subgraph A box around stuff
                id3 ==> id6
            end

            style id1 fill:green,stroke:black
            style id2 fill:white,stroke:#f66,stroke-dasharray: 5, 5
            style id3 fill:#66f,stroke:#f6f,stroke-width:4px
            style id5 fill:orange,stroke:white
            style id6 fill:yellow,stroke:blue

And would produce the following chart:

.. mermaid::
    :align: center

    flowchart LR
    
        id1(Box with round corner)
        id2([Stadium])
        id3[(Database)]
        id5{{Hex}}
        id6[\Parallelogram\]

        id1-->id2
        id1-->id3
        id2-.-id5

        subgraph A box around stuff
            id3 ==> id6
        end

        style id1 fill:green,stroke:black
        style id2 fill:white,stroke:#f66,stroke-dasharray: 5, 5
        style id3 fill:#66f,stroke:#f6f,stroke-width:4px
        style id5 fill:orange,stroke:white
        style id6 fill:yellow,stroke:blue

You can see more on cool things you can do with mermaid charts in the :ref:`Mermaid documentation <cool_mermaid>`.

Embedding Charts with SVG
``````````````````````````````````````

Another way is to create ``.svg`` files and embed them into the documentation. This is done using the ``.. raw:: html`` directive.

.. code-block:: RST

    .. raw:: html
        :file: ../img/nudging_flowchart.svg  

Produces:

.. raw:: html
    :file: ../img/nudging_flowchart.svg  

Embedding Videos
-----------------

You can embed videos with the ``.. raw:: html`` directive. This is done by copying the html code from the YouTube video and pasting it into the ``.rst`` file. For example, the following code embeds a video into this page.

To get the code, go to the YouTube video, click on the "Share" button, and then click on the "Embed" button. Copy the text and paste it between the <div style....> and </div> tags.

.. code-block:: RST

    .. raw:: html

        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 50%; height: 50%; margin: 2em auto; text-align: center;">
            <iframe width="560" height="315" src="https://www.youtube.com/embed/lPQ9ZGAD33k?si=cErRdwXPo98syDK3" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
        </div>

.. raw:: html

    <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 50%; height: 50%; margin: 2em auto; text-align: center;">
        <iframe width="560" height="315" src="https://www.youtube.com/embed/lPQ9ZGAD33k?si=cErRdwXPo98syDK3" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
    </div>