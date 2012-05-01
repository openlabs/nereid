# -*- coding: UTF-8 -*-
'''
    nereid.backend.general

    A sample API Class for Connection and Dispatch Interface

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
from ..threading import local
from ..exceptions import NotImplementedYet

class Connection(object):
    """Generic Connection class

    The connection to the ORM is directly made. Both
    Tryton and OpenERP uses the same approach of loading 
    modules of a specific database based on the installed
    modules. However, this is an expensive process and 
    cannot be used everytime for a request. Hence the process
    must be done only once.

    Hence the connection object is a callable which loads the
    connection to the DB (via ORM) in the initiation of the class
    """

    __slots__ = ('database_name', 'database', 'pool', 'config')

    def __init__(self, config):
        """Load the connection to the ORM (DB Connect) and connect

        :param config: Config Object/Dictionary
        """
        self.config = config
        self.connect()

    def connect(self):
        """Connect to the database and assign class vars
        database_name, database and pool
        """
        raise NotImplementedYet()


class Transaction(object):
    """An easy to use API to the backend to avoid the abstract
    classes from handling the difference of Tryton and OpenERP and
    their versions.

    This is implemented as a context manager to be used with the 'with'
    statement

    Inspired by the transaction contextualisation of Tryton
    """

    __slots__ = ('connection', 'user', 'context')

    def __init__(self, connection, user, context=None):
        """

        :param connection: Instance of a Backend Connection
        :param user: ID of the user
        :param context: Context - for OpenERP/Tryton
        """
        self.connection = connection
        self.user = user
        self.context = context

    def __enter__(self):
        """Start the transaction,
        set the transaction object to the
        local threaded env
        """
        local.transaction = self.start()
        return local.transaction

    def __exit__(self, type_, value, traceback):
        """
        End of transaction
        """
        local.transaction = None

        if isinstance(value, Exception):
            self._cursor_rollback()
        else:
            self._cursor_commit()
        self.stop()

    def start(self):
        """Start the transaction and
        return the transaction object instance
        """
        raise NotImplementedYet()

    def _cursor_commit(self):
        "Commit the cursor"
        raise NotImplementedYet()

    def _cursor_rollback(self):
        "Cancel the transaction changes"
        raise NotImplementedYet()

    def stop(self):
        "Stop the transaction"
        raise NotImplementedYet()

    def get_user_context(self, user=None):
        """Return a user's context

        if the user argument is given use that for getting context
        else get context of user from the transaction
        """
        raise NotImplementedYet()

    def id_from_login(self, login):
        "Return a user ID from the login"
        raise NotImplementedYet()

    def user_from_login(self, login):
        "Return Current user from login"
        raise NotImplementedYet()

    def dispatch(self, method, *args, **kwargs):
        """Dispatch a given request to the given method
        while giving all due respect to the backend's used
        function signature

        For example:

            OpenERP hs a common func signature of
            (self, cursor, user, *args, **kwargs)

        while:

            Tryton 1.8+ has a signature with contextualised
            cursor, user and context like:
            (self, *args, **kwargs)

        :param method: Bound method of a class
        :param args: Positional Arguments
        :param kwargs: keyword arguments
        """
        raise NotImplementedYet()

    def model_method_dispatch(self, model_name, method_name,
            *args, **kwargs):
        "Load model from pool, get method and then call"
        method = getattr(self.connection.pool.get(model_name), method_name)
        return self.dispatch(method, *args, **kwargs)
