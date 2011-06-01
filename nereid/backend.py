# -*- coding: UTF-8 -*-
'''
    nereid.backend

    Backed - Tryton specific features

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
from werkzeug import abort

from .helpers import Pagination, QueryPagination
from .config import ConfigAttribute


class TransactionManager(object):

    def __init__(self, database_name, user, context=None):
        self.database_name = database_name
        self.user = user
        self.context = context if context is not None else {}

    def __enter__(self):
        from trytond.transaction import Transaction
        Transaction().start(self.database_name, self.user, self.context.copy())
        return Transaction()

    def __exit__(self, type, value, traceback):
        from trytond.transaction import Transaction
        Transaction().stop()


class BackendMixin(object):
    """Special class to mix the backend connection
    into nereid"""

    _pool = None
    _database = None

    #: Configuration file for Tryton
    tryton_configfile = ConfigAttribute('TRYTON_CONFIG')
    database_name = ConfigAttribute('DATABASE_NAME')
    tryton_user = ConfigAttribute('TRYTON_USER')
    tryton_context = ConfigAttribute('TRYTON_CONTEXT')

    def __init__(self, *args, **kwargs):
        if self.tryton_configfile is not None:
            from trytond.config import CONFIG
            CONFIG.configfile = self.tryton_configfile
            CONFIG.load()

    def load_connection(self):
        "Actual loading of connection takes place here"
        from trytond.backend import Database
        from trytond.modules import register_classes
        register_classes()
        from trytond.pool import Pool

        # Load pool
        self._database = Database(self.database_name).connect()
        self._pool = Pool(self.database_name)
        self._pool.init()

        # Load context
        user_obj = self._pool.get('res.user')
        self.tryton_context.update(user_obj.get_preferences())

    @property
    def pool(self):
        "Return an initialised pool to the ORM"
        if not self._pool:
            self.load_connection()
        return self._pool

    @property
    def database(self):
        "Return connection to Database backend of tryton"
        if not self._database:
            self.load_connection()
        return self._database

    @property
    def transaction(self):
        """Allows the use of the transaction as a context manager. 

        Example::

        with app.transaction as transaction:
            Party = app.pool.get('party.party')
            party_ids = Party.search([ ])
            print party_ids
        """
        return TransactionManager(
            self.database_name, self.tryton_user, self.tryton_context)

    def get_method(self, model_method):
        """Get the object from pool and fetch the method from it

        model_method is expected to be '<model>.<method>'
        """
        model_method_split = model_method.split('.')
        model = '.'.join(model_method_split[:-1])
        method = model_method_split[-1]

        try:
            return getattr(self.pool.get(model), method)
        except AttributeError:
            raise Exception("Method %s not in Model %s" % (method, model))


class ModelPagination(object):
    """A mixin ancestor that models in tryton could inherit 
    if they will need to do pagination"""


    def paginate(self, domain, page, per_page=20, error_out=True, order=None):
        """Returns `per_page` items from page `page`.  By default it will
        abort with 404 if no items were found and the page was less than
        1.  This behavior can be disabled by setting `error_out` to `False`.

        Returns an :class:`Pagination` object.
        """
        raise DeprecationWarning("ModelPagination will be deprecated. See "
            "https://bitbucket.org/openlabs/nereid2/wiki/"
            "deprecation-of-model-pagination")

        if error_out and page < 1:
            abort(404)

        pagination = Pagination(self, domain, page, per_page, order)
        if not pagination.pages and error_out:
            abort(404)

        return pagination
