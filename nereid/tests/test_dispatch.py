# -*- coding: utf-8 -*-
# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import unittest
from contextlib import contextmanager

import trytond.tests.test_tryton
from trytond import backend
from trytond.config import CONFIG
from trytond.transaction import Transaction
from trytond.tests.test_tryton import POOL, USER, DB, DB_NAME, CONTEXT
from werkzeug.contrib.sessions import FilesystemSessionStore
from nereid import Nereid
from nereid.signals import transaction_start
from nereid.sessions import Session
from nereid.contrib.locale import Babel

from test_templates import BaseTestCase


class NereidTestApp(Nereid):
    """
    A custom Nereid Subclass which uses the transaction handling as it is the
    subject of this test.
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
        self._database = DB
        self._pool = POOL


class TestDispatcherRetry(BaseTestCase):
    """
    Test the transaction retry mechanism in dispatcher

    This test will end up committing code and hence it should be the last test
    in a test suite as there would be certain side effects.
    """
    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid_test')
        super(TestDispatcherRetry, self).setUp()

        self.error_counter = 0

    def get_app(self, **options):
        app = NereidTestApp(
            template_folder=os.path.abspath(
                os.path.join(os.path.dirname(__file__), 'templates')
            )
        )
        if 'SECRET_KEY' not in options:
            options['SECRET_KEY'] = 'secret-key'
        app.config['TEMPLATE_PREFIX_WEBSITE_NAME'] = False
        app.config.update(options)
        app.config['DATABASE_NAME'] = DB_NAME
        app.config['DEBUG'] = True
        app.session_interface.session_store = \
            FilesystemSessionStore('/tmp', session_class=Session)

        # Initialise the app now
        app.initialise()

        # Load babel as its a required extension anyway
        Babel(app)
        return app

    def test_0010_test_failure_counter(self):
        context = CONTEXT.copy()
        with Transaction().start(DB_NAME, USER, context=context) as txn:
            self.setup_defaults()
            app = self.get_app()

            txn.cursor.commit()

        DatabaseOperationalError = backend.get('DatabaseOperationalError')

        @transaction_start.connect
        def incr_error_count(app):
            """
            Subscribe to the transaction_start to increment the counter
            """
            self.error_counter += 1

        CONFIG['retry'] = 4

        with app.test_client() as c:
            try:
                c.get('fail-with-transaction-error')
            except DatabaseOperationalError:
                self.assertEqual(self.error_counter, 5)


def suite():
    "Nereid Dispatcher test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestDispatcherRetry),
    ])
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
