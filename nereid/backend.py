# -*- coding: UTF-8 -*-
'''
    nereid.backend

    Backed - Tryton specific features

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''
from trytond.config import CONFIG
from trytond.modules import register_classes
from trytond.pool import Pool
from trytond.backend import Database
from trytond.transaction import Transaction

from .config import ConfigAttribute

register_classes()


class TransactionManager(object):

    def __init__(self, database_name, user, context=None):
        self.database_name = database_name
        self.user = user
        self.context = context

    def __enter__(self):
        Transaction().start(self.database_name, self.user, self.context)

    def __exit__(self, type, value, traceback):
        # TODO: Handle the case where exception is thrown
        Transaction().stop()


class BackendMixin(object):
    """Special class to mix the backend connection
    into nereid"""

    _pool = None
    _database = None

    #: Configuration file for Tryton
    tryton_configfile = ConfigAttribute('TRYTON_CONFIG')
    database_name = ConfigAttribute('DATABASE_NAME')
    tryton_config = CONFIG

    def __init__(self, *args, **kwargs):
        CONFIG.configfile = self.tryton_configfile
        CONFIG.load()

    def load_connection(self):
        "Actual loading of connection takes place here"
        self._database = Database(self.database_name).connect()
        self._pool = Pool(self.database_name)
        self._pool.init()

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
    def context(self):
        """Must return the context. This must ideally return
        the context relevant to the currently logged in user.
        """
        # TODO
        return None

    @property
    def transaction(self):
        """Allows the use of the transaction as a context manager. 

        Example::

        with app.transaction as transaction:
            Party = app.pool.get('party.party')
            party_ids = Party.search([ ])
            print party_ids
        """
        return TransactionManager(self.database_name, 0, self.context)

    def get_method(self, model_method):
        """Get the object from pool and fetch the method from it

        model_method is expected to be '<model>.<method>'
        """
        model_method_split = model_method.split('.')
        model = '.'.join(model_method_split[:-1])
        method = model_method_split[-1]

        return getattr(self.pool.get(model), method)
