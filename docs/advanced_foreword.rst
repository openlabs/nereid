.. _advanced_foreword:

If you already use Flask
========================

If you are already used to programming in Flask you would be keen to know
the main differences Nereid has with Flask. If you do not already use
Flask, and is not familiar with Tryton this document might not make a 
lot of sense to you. 

URL Routes
----------

Flask applications use decorators to bind a function that should handle
the request to a URL pattern. A basic example of this is::

    @app.route('/')
    def index():
        return 'Index Page'

    @app.route('/hello')
    def hello():
        return 'Hello World'

But, in the case of Nereid, the request handlers are methods in Model
classes loaded in a Tryton Pool. In addition, to maintain the modularity
of Tryton (where modules loaded are not modules in the python path, but
the modules installed in a specific database), the use of decorators even
using Flask blueprints is not possible. So for nereid, the URL rules are
stored to a database::

    class Customer(ModelSQL, ModelView):
        """
        A fictional customer model
        """
        _name = "customer.customer"
        _description = __doc__

        def index(self):
            return 'Index Page'

        def hello(self):
            """
            Render a profile page for the customer
            """
            return 'Hello World'


and to create the URL rule, you could add them to an xml file

.. code-block:: python
    :emphasize-lines: 2,3,9,10
       
    <record id="index_handler" model="nereid.url_rule">
        <field name="rule">/</field>
        <field name="endpoint">customer.customer.index</field>
        <field name="sequence" eval="05" />
        <field name="url_map" ref="nereid.default_url_map" />
    </record>

    <record id="hello_handler" model="nereid.url_rule">
        <field name="rule">/hello</field>
        <field name="endpoint">customer.customer.hello</field>
        <field name="sequence" eval="10" />
        <field name="url_map" ref="nereid.default_url_map" />
    </record>


Continue to :ref:`installation` or the :ref:`quickstart`.
