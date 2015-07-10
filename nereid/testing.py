# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from contextlib import contextmanager

import jinja2
import unittest
from nereid.sessions import Session
from nereid.contrib.locale import Babel
from werkzeug.contrib.sessions import FilesystemSessionStore

from nereid import Nereid
from flask.globals import _request_ctx_stack


class NereidTestApp(Nereid):
    """
    A Nereid app which works by removing transaction handling around the wsgi
    app
    """

    def __init__(self, **config):
        super(NereidTestApp, self).__init__(**config)
        self.config['WTF_CSRF_ENABLED'] = False

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

    def dispatch_request(self):
        """
        Skip the transaction handling and call the _dispatch_request
        """
        req = _request_ctx_stack.top.request
        if req.routing_exception is not None:
            self.raise_routing_exception(req)

        rule = req.url_rule
        # if we provide automatic options for this URL and the
        # request came with the OPTIONS method, reply automatically
        if getattr(rule, 'provide_automatic_options', False) \
           and req.method == 'OPTIONS':
            return self.make_default_options_response()

        language = 'en_US'
        if req.nereid_website:
            # If this is a request specific to a website
            # then take the locale from the website
            language = req.nereid_locale.language.code

        # pop locale if specified in the view_args
        req.view_args.pop('locale', None)
        active_id = req.view_args.pop('active_id', None)

        return self._dispatch_request(req, language, active_id)


def get_app(**options):
    app = NereidTestApp()
    if 'SECRET_KEY' not in options:
        options['SECRET_KEY'] = 'secret-key'
    app.config.update(options)
    from trytond.tests.test_tryton import DB_NAME
    app.config['DATABASE_NAME'] = DB_NAME
    app.config['DEBUG'] = True
    app.session_interface.session_store = \
        FilesystemSessionStore('/tmp', session_class=Session)

    # loaders is usually lazy loaded
    # Pre-fetch it so that the instance attribute _loaders will exist
    app.jinja_loader.loaders

    # Initialise the app now
    app.initialise()

    # Load babel as its a required extension anyway
    Babel(app)
    return app


class NereidTestCase(unittest.TestCase):

    @property
    def _templates(self):
        if hasattr(self, 'templates'):
            return self.templates
        return {}

    def get_app(self, **options):
        app = get_app(**options)
        app.jinja_loader._loaders.insert(0, jinja2.DictLoader(self._templates))
        return app
