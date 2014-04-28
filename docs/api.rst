.. _api:

API Reference
=============

.. module:: nereid 


Application Object
------------------

.. autoclass:: Nereid
   :members:


Templating
----------

.. autoclass:: nereid.templating.LazyRenderer
   :members:

.. autoclass:: nereid.templating.SiteNamePrefixLoader
   :members:

.. autoclass:: nereid.templating.ModuleTemplateLoader
   :members:

.. autofunction:: nereid.templating.render_template

Helpers
-------

.. autofunction:: nereid.helpers.url_for
.. autofunction:: nereid.helpers.route

Backend - Tryton Connection
---------------------------

.. automodule:: nereid.backend
    :members:

Testing Helpers
---------------

.. automodule:: nereid.testing 
    :members:
