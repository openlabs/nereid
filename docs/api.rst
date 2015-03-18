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

.. autoclass:: nereid.templating.ModuleTemplateLoader
   :members:

.. autofunction:: nereid.templating.render_template
.. autofunction:: nereid.templating.render_email

Helpers
-------

.. autofunction:: nereid.helpers.url_for
.. autofunction:: nereid.helpers.route
.. autofunction:: nereid.helpers.context_processor
.. autofunction:: nereid.helpers.template_filter

Testing Helpers
---------------

.. automodule:: nereid.testing 
    :members:
