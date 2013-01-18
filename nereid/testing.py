# -*- coding: utf-8 -*-
"""
    nereid.testing
    ~~~~~~~~~~~~~~

    Implements test support helpers.  This module is lazily imported
    and usually not used in production environments.

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: GPLv3, see LICENSE for more details.
"""
from contextlib import contextmanager

import jinja2
import unittest
from flask.helpers import locked_cached_property
from nereid.sessions import Session
from nereid.contrib.locale import Babel
from werkzeug.contrib.sessions import FilesystemSessionStore

from nereid import Nereid


class NereidTestApp(Nereid):
    """
    A Nereid app which works by removing transaction handling around the wsgi
    app
    """
    @property
    def root_transaction(self):
        """
        There is no need of a separate root transaction as everything could
        be loaded in the transaction context provided in the test case
        """
        @contextmanager
        def do_nothing():
            yield
        return do_nothing()

    @locked_cached_property
    def jinja_loader(self):
        """
        The jinja loader needs to be implemented by the test client and
        provided by the test case.
        """
        raise Exception("Template loading has to be implemented by TestCase")

    def load_backend(self):
        """Just reuse the pool and DB already loaded by the tryton test loader
        """
        from trytond.tests.test_tryton import DB, POOL
        self._database = DB
        self._pool = POOL

    def wsgi_app(self, environ, start_response):
        """The actual WSGI application.  This is not implemented in
        `__call__` so that middlewares can be applied without losing a
        reference to the class.  So instead of doing this::

            app = MyMiddleware(app)

        It's a better idea to do this instead::

            app.wsgi_app = MyMiddleware(app.wsgi_app)

        Then you still have the original application object around and
        can continue to call methods on it.

        In Nereid the transaction is introduced after the request_context
        is loaded.

        :param environ: a WSGI environment
        :param start_response: a callable accepting a status code,
                               a list of headers and an optional
                               exception context to start the response
        """
        if not self.initialised:
            self.initialise()

        with self.request_context(environ):
            response = self.full_dispatch_request()
            return response(environ, start_response)


class NereidTestCase(unittest.TestCase):

    def _get_template(self, name):
        """
        A template loader passed directly into the test app. It is not
        recommended to subclass this. Instead, implement
        :meth:`get_template_source` in your test case.

        The method has to return either an unicode string with the
        template source, a tuple in the form (source, filename, uptodatefunc)
        or None if the template does not exist.

        Example::

            def get_template_source(self, name):
                if name == "index.html":
                    return "Hello World"
        """
        try:
            return self.get_template_source(name)
        except AttributeError:
            return None

    def get_app(self, **options):
        app = NereidTestApp()
        app.config.update(options)
        from trytond.tests.test_tryton import DB_NAME
        app.config['DATABASE_NAME'] = DB_NAME
        app.config['DEBUG'] = True
        app.session_interface.session_store = \
            FilesystemSessionStore('/tmp', session_class=Session)

        app.jinja_loader = jinja2.FunctionLoader(self._get_template)

        # Initialise the app now
        app.initialise()

        # Load babel as its a required extension anyway
        Babel(app)
        return app
