# -*- coding: UTF-8 -*-
'''
    nereid.backend

    Backed - Tryton specific features

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
import json

from otcltools.general.pagination import Pagination as BasePagination
from werkzeug import abort
from werkzeug.utils import cached_property

from .config import ConfigAttribute


class TransactionManager(object):

    def __init__(self, database_name, user, context=None):
        self.database_name = database_name
        self.user = user
        self.context = context

    def __enter__(self):
        from trytond.transaction import Transaction
        Transaction().start(self.database_name, self.user, self.context)
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


class Pagination(BasePagination):
    """
    General purpose paginator for doing pagination
    """

    def __init__(self, obj, domain, page, per_page, order=None):
        """
        :param klass: The object itself. pass self within tryton object
        :param domain: Domain for search in tryton
        :param per_page: Items per page
        :param page: The page to be displayed
        """
        self.obj = obj
        self.domain = domain
        self.order = order
        super(Pagination, self).__init__(page, per_page)

    @cached_property
    def count(self):
        """
        Returns the count of entries
        """
        return self.obj.search(domain=self.domain, count=True)

    def all_items(self):
        """Returns complete set of items"""
        ids = self.obj.search(self.domain)
        return self.obj.browse(ids)

    def items(self):
        """Returns the list of browse records of items in the page
        """
        ids = self.obj.search(self.domain, offset=self.offset,
            limit=self.per_page, order=self.order)
        return self.obj.browse(ids)

    @property
    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        return self.obj.paginate(self.page - 1, self.per_page, error_out)

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        return self.obj.paginate(self.page + 1, self.per_page, error_out)


class ModelPagination(object):
    """A mixin ancestor that models in tryton could inherit 
    if they will need to do pagination"""


    def paginate(self, domain, page, per_page=20, error_out=True):
        """Returns `per_page` items from page `page`.  By default it will
        abort with 404 if no items were found and the page was less than
        1.  This behavior can be disabled by setting `error_out` to `False`.

        Returns an :class:`Pagination` object.
        """
        if error_out and page < 1:
            abort(404)

        pagination = Pagination(self, domain, page, per_page)
        if not pagination.pages and error_out:
            abort(404)

        return pagination
