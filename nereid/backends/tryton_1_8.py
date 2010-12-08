# -*- coding: UTF-8 -*-
'''
    nereid.backend.tryton_1_8

    Tryton 1.8 Backend Interface
    == Major change is contextualisation in Tryton ==

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: GPLv3, see LICENSE for more details
'''

from trytond.config import CONFIG as TrytonConfig
from trytond.modules import register_classes
from trytond.pool import Pool
from trytond.backend import Database
from trytond.transaction import Transaction as TrytonTransaction

from .connection import Connection as BaseConnection
from .connection import Transaction as BaseTransaction
from .paginator import Pagination as BasePagination

ROOT_USER = 0

class Connection(BaseConnection):
    "Implements Connection to Tryton 1.8"

    __slots__ = ()

    def connect(self):
        "Connect to Tryton"

        # Register classes populates the pool of models:
        register_classes()

        TrytonConfig.configfile = self.config['TRYTON_CONFIG']
        TrytonConfig.load()

        # Load pool and database
        self.database = Database(self.config['DATABASE_NAME']).connect()
        self.pool = Pool(self.config['DATABASE_NAME'])
        self.pool.init()


class Transaction(BaseTransaction):
    """Interface with Tryton

    The cursor is added as an instance variable so that
    this class itself can be used as the transaction
    object.
    """

    __slots__ = ('cursor')

    def start(self):
        transaction = TrytonTransaction().start(
            self.config['DATABASE_NAME'],
            self.user,
            self.context
            )
        return transaction

    def stop(self):
        TrytonTransaction().stop()

    def _cursor_commit(self):
        TrytonTransaction().cursor.commit()

    def _cursor_rollback(self):
        TrytonTransaction().cursor.rollback()

    def get_user_context(self, user=None):
        return self.model_method_dispatch(
            'res.user', 'get_preferences', context_only=True
            )

    def id_from_login(self, login):
        "Returns the ID of the user identified by login name"
        user_obj = self.connection.pool.get('res.user')
        user_ids = user_obj.search([('login', '=', login)], limit=1)
        return user_ids and user_ids[0] or False

    def user_from_login(self, login):
        "Return Current user from login"
        user_id = self.id_from_login(login)
        return self.model_method_dispatch(
            'res.user', 'browse', user_id 
        )

    def dispatch(self, method, *args, **kwargs):
        """Dispatch with the signature of cursor, user and context
        """
        if 'context' in kwargs:
            context = kwargs.pop('context')
            with TrytonTransaction().set_context(context):
                return method(*args, **kwargs)

        return method(*args, **kwargs)


class Pagination(BasePagination):
    """
    Paginator for Tryton 1.8
    """

    @property
    def count(self):
        """
        Returns the count of entries
        """
        return self.klass.search(
            domain=self.domain,
            offset=self.offset,
            limit=self.per_page,
            order=self.order,
            count=True
            )

    @property
    def entries(self):
        """
        Returns the list of browse records
        """
        ids = self.klass.search(
            domain=self.domain,
            offset=self.offset,
            limit=self.per_page,
            order=self.order,
            )
        return self.klass.browse(ids)

