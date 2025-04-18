.. _doc_sphinx:

Sphinx Documentation Principles
================================

First, you can review Sphinx's reStructuredText Primer `here <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_. But some basics that are super useful:

Headings order
---------------

Underneath each heading you can repeat one of the following characters under the entire heading text:

``= - ` : . ' " ~ ^ _ * + #``

This is also the order that the headers are used, and this affects the way a table of contents is rendered and which sections are nested where.

Ex:

  .. code-block:: RST

        Sphinx Documenation Principles
        ==============================
        
        Headings order
        ---------------

This creates the headings above. Note that the header characters extend to the full extent of the text above them. If they are short they will not work as section headers.

BayDeltaSCHISM Specifics
-------------------------

Any .rst files that relate to the `User Guide <https://cadwrdeltamodeling.github.io/BayDeltaSCHISM/user_guide.html>`_ are held in the ``docsrc/topics`` folder. **No other .rst files are found there.**

Similarly all documentation files are found in the ``docsrc/meta_doc`` folder.

