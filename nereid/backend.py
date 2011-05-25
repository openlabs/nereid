# -*- coding: UTF-8 -*-
'''
    nereid.backend

    Backed - Tryton specific features

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
from otcltools.general.pagination import Pagination as BasePagination
from werkzeug import abort
from werkzeug.utils import cached_property

from .config import ConfigAttribute
from .globals import request
from .ctx import has_request_context


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


class Pagination(BasePagination):
    """General purpose paginator for doing pagination which can be used by 
    passing a search domain .Remember that this means the query will be built
    and executed and passed on which could be slower than writing native SQL 
    queries. While this fits into most use cases, if you would like to use
    a SQL query rather than a domain use :class:QueryPagination instead
    """

    # The counting of all possible records can be really expensive if you
    # have too many records and the selectivity of the query is low. For 
    # example -  a query to display all products in a website would be quick
    # in displaying the products but slow in building the navigation. So in 
    # cases where this could be frequent, the value of count may be cached and
    # assigned to this variable
    _count = None

    def __init__(self, obj, domain, page, per_page, order=None):
        """
        :param obj: The object itself. pass self within tryton object
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
        if self.ids_domain():
            return len(self.domain[0][2])
        if self._count is not None:
            return self._count
        return self.obj.search(domain=self.domain, count=True)

    def all_items(self):
        """Returns complete set of items"""
        if self.ids_domain():
            ids = self.domain[0][2]
        else:
            ids = self.obj.search(self.domain)
        return self.obj.browse(ids)

    def ids_domain(self):
        """Returns True if the domain has only IDs and can skip SQL fetch
        to directly browse the records. Else a False is returned
        """
        return (len(self.domain) == 1) and \
            (self.domain[0][0] == 'id') and \
            (self.domain[0][1] == 'in') and \
            (self.order is None)

    def items(self):
        """Returns the list of browse records of items in the page
        """
        if self.ids_domain():
            ids = self.domain[0][2][self.offset:self.offset + self.per_page]
        else:
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


class QueryPagination(BasePagination):
    """A fast implementation of pagination which uses a SQL query for 
    generating the IDS and hence the pagination"""

    def __init__(self, obj, search_query, count_query, page, per_page):
        """
        :param search_query: Query to be used for search. It must not include
            an OFFSET or LIMIT as they would be automatically added to the 
            query
        :param count_query: Query to be used to get the count of the pagination
            use a query like `SELECT 1234 AS id` for a query where you do not
            want to manipulate the count
        :param per_page: Items per page
        :param page: The page to be displayed
        """
        self.obj = obj
        self.search_query = search_query
        self.count_query = count_query
        super(QueryPagination, self).__init__(page, per_page)

    @cached_property
    def count(self):
        "Return the count of the Items"
        from trytond.transaction import Transaction
        with Transaction().new_cursor() as transaction:
            transaction.cursor.execute(self.count_query)
            return transaction.cursor.fetchone()[0]

    def all_items(self):
        """Returns complete set of items"""
        from trytond.transaction import Transaction
        with Transaction().new_cursor() as transaction:
            transaction.cursor.execute(self.search_query)
            rv = [x[0] for x in transaction.cursor.fetchall()]
        return self.obj.browse(rv)

    def items(self):
        """Returns the list of browse records of items in the page
        """
        from trytond.transaction import Transaction
        limit_string = ' LIMIT %d' % self.per_page
        offset_string = ' OFFSET %d' % self.offset
        with Transaction().new_cursor() as transaction:
            transaction.cursor.execute(''.join([
                self.search_query, limit_string, offset_string
                ]))
            rv = [x[0] for x in transaction.cursor.fetchall()]
        return self.obj.browse(rv)


class ModelPagination(object):
    """A mixin ancestor that models in tryton could inherit 
    if they will need to do pagination"""


    def paginate(self, domain, page, per_page=20, error_out=True, order=None):
        """Returns `per_page` items from page `page`.  By default it will
        abort with 404 if no items were found and the page was less than
        1.  This behavior can be disabled by setting `error_out` to `False`.

        Returns an :class:`Pagination` object.
        """
        if error_out and page < 1:
            abort(404)

        pagination = Pagination(self, domain, page, per_page, order)
        if not pagination.pages and error_out:
            abort(404)

        return pagination
