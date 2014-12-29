# -*- coding: utf-8 -*-
# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import warnings

import jinja2
from test_templates import BaseTestCase
from trytond.pool import PoolMeta, Pool
from trytond.tests.test_tryton import USER, DB_NAME, CONTEXT, POOL
from trytond.transaction import Transaction
from nereid import url_for, template_filter


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


class NereidWebsite:
    __metaclass__ = PoolMeta
    __name__ = 'nereid.website'

    @classmethod
    @template_filter()
    def reverse_test(cls, s):
        return s[::-1]


class TestHelperFunctions(BaseTestCase):
    '''
    Test case to test various helper functions introduced by nereid
    '''

    @classmethod
    def setUpClass(cls):
        Pool.register(
            NereidWebsite,
            module='nereid', type_='model'
        )
        POOL.init(update=['nereid'])

    @classmethod
    def tearDownClss(cls):
        mpool = Pool.classes['model'].setdefault('nereid', [])
        mpool.remove(NereidWebsite)
        POOL.init(update=['nereid'])

    def test_template_filter(self):
        '''
        Test the template filter decorator implementation
        '''
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            templates = {
                'home.jinja': "{{ 'abc'|reverse_test }}"
            }
            app = self.get_app()
            # loaders is usually lazy loaded
            # Pre-fetch it so that the instance attribute _loaders will exist
            app.jinja_loader.loaders
            app.jinja_loader._loaders.insert(0, jinja2.DictLoader(templates))

            with app.test_client() as c:
                response = c.get('/')
                self.assertEqual(response.data, 'cba')


def suite():
    "Nereid Helpers test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests([
        unittest.TestLoader().loadTestsFromTestCase(TestURLfor),
        unittest.TestLoader().loadTestsFromTestCase(TestHelperFunctions),
    ])
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
