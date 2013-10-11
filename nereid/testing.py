#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from contextlib import contextmanager

import jinja2
import unittest
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

    def load_backend(self):
        """
        Just reuse the pool and DB already loaded by the tryton test loader
        """
        from trytond.tests.test_tryton import DB, POOL
        self._database = DB
        self._pool = POOL

    def wsgi_app(self, environ, start_response):
        """
        The actual WSGI application.  This is not implemented in
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
            try:
                response = self.full_dispatch_request()
            except Exception, e:
                response = self.make_response(self.handle_exception(e))
            return response(environ, start_response)


class NereidTestCase(unittest.TestCase):

    @property
    def _templates(self):
        if hasattr(self, 'templates'):
            return self.templates
        return {}

    def get_app(self, **options):
        app = NereidTestApp()
        app.config.update(options)
        from trytond.tests.test_tryton import DB_NAME
        app.config['DATABASE_NAME'] = DB_NAME
        app.config['DEBUG'] = True
        app.session_interface.session_store = \
            FilesystemSessionStore('/tmp', session_class=Session)

        # loaders is usually lazy loaded
        # Pre-fetch it so that the instance attribute _loaders will exist
        app.jinja_loader.loaders
        app.jinja_loader._loaders.insert(0, jinja2.DictLoader(self._templates))

        # Initialise the app now
        app.initialise()

        # Load babel as its a required extension anyway
        Babel(app)
        return app
