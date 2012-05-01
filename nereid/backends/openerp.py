# -*- coding: UTF-8 -*-
'''
    nereid.backend.openerp

    OpenERP Backend Interface

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
import sys

from ..threading import local

from .connection import Connection as BaseConnection
from .connection import Transaction as BaseTransaction
from .paginator import Pagination as BasePagination

ROOT_USER = 1


class Connection(BaseConnection):
    "Implements Connection to OpenERP"

    __slots__ = ()

    def connect(self):
        "Connect to OpenERP"

        # The following modules need to be imported from OE path
        # (Since OE doesnt work as a module) for the
        # funcionalities of OpenERP to work, however, they
        # can neither be imported, nor do they need to be used here
        sys.path.append(self.config['OPENERP_ROOT_PATH'])

        # pylint: disable-msg=F0401
        # pylint: disable-msg=W0612
        import pooler
        import netsvc
        import osv
        import workflow
        import report
        import service
        # pylint: enable-msg=F0401
        # pylint: enable-msg=W0612

        # Load pool and database
        self.database, self.pool = pooler.get_db_and_pool(
            self.config['DATABASE_NAME']
            )


class Transaction(BaseTransaction):
    """Interface with OpenERP

    The cursor is added as an instance variable so that
    this class itself can be used as the transaction
    object.
    """

    __slots__ = ('cursor')

    def start(self):
        self.cursor = self.connection.database.cursor()
        return self

    def stop(self):
        self.cursor.close()
        self.cursor = None

    def _cursor_commit(self):
        self.cursor.commit()

    def _cursor_rollback(self):
        self.cursor.rollback()

    def get_user_context(self, user=None):
        user_obj = self.connection.pool.get('res.users')
        user = user or self.user
        # TODO: Avoid the overridings in the configuration module
        return user_obj.get_context(self.cursor, user)

    def id_from_login(self, login):
        "Returns the ID of the user identified y login name"
        user_obj = self.connection.pool.get('res.users')
        user_ids = user_obj.search(
            self.cursor, self.user,
            [('login', '=', login)], limit=1)
        return user_ids and user_ids[0] or False

    def user_from_login(self, login):
        "Return Current user from login"
        user_id = self.id_from_login(login)
        return self.model_method_dispatch(
            'res.users', 'browse', user_id, self.context
        )

    def dispatch(self, method, *args, **kwargs):
        """Dispatch with the signature of cursor, user and context
        """
        if 'context' not in kwargs:
            kwargs['context'] = self.get_user_context()
        return method(self.cursor, self.user, *args, **kwargs)


class Pagination(BasePagination):
    """
    Paginator for Openerp
    """

    @property
    def count(self):
        """
        Returns the count of entries
        """
        return self.klass.search(
            local.transaction.cursor,
            local.request.tryton_user.id,
            args=self.domain,
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
            local.transaction.cursor,
            local.request.tryton_user.id,
            args=self.domain,
            offset=self.offset,
            limit=self.per_page,
            order=self.order,
            )
        return self.klass.browse(
            local.transaction.cursor,
            local.request.tryton_user.id,
            ids)

