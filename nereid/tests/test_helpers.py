# -*- coding: utf-8 -*-
# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import warnings

from test_templates import BaseTestCase
from trytond.tests.test_tryton import USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from nereid import url_for


class TestURLfor(BaseTestCase):
    """
    Test the functionality of the url_for helper
    """

    def test_0010_simple(self):
        """
        Generate a simple URL
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_request_context('/'):
                self.assertEqual(url_for('nereid.website.home'), '/')

    def test_0020_external(self):
        """
        Create an external URL
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_request_context('/'):
                self.assertEqual(
                    url_for('nereid.website.home', _external=True),
                    'http://localhost/'
                )

    def test_0030_schema(self):
        """
        Change the schema to https
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_request_context('/'):
                self.assertEqual(
                    url_for('nereid.website.home',
                            _external=True, _scheme='https'),
                    'https://localhost/'
                )

            with app.test_request_context('/'):
                # Check for the to be deprecated _secure argument
                with warnings.catch_warnings(record=True) as w:
                    self.assertEqual(
                        url_for('nereid.website.home', _secure=True),
                        'https://localhost/'
                    )
                    self.assertEqual(len(w), 1)


def suite():
    "Nereid Helpers test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestURLfor),
    ])
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
