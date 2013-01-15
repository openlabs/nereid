#!/usr/bin/env python
"""

    Test the currency URL handling

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from nereid.testing import NereidTestCase
from trytond.transaction import Transaction


class TestCurrency(NereidTestCase):
    """
    Test Currency
    """

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid')

        self.nereid_website_obj = POOL.get('nereid.website')
        self.nereid_permission_obj = POOL.get('nereid.permission')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.url_map_obj = POOL.get('nereid.url_map')
        self.company_obj = POOL.get('company.company')
        self.currency_obj = POOL.get('currency.currency')
        self.language_obj = POOL.get('ir.lang')
        self.party_obj = POOL.get('party.party')

    def setup_defaults(self):
        """
        Setup the defaults
        """
        usd = self.currency_obj.create({
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        })
        self.company_id = self.company_obj.create({
            'name': 'Openlabs',
            'currency': usd
        })
        self.company = self.company_obj.browse(self.company_id)
        self.guest_user_id = self.nereid_user_obj.create({
            'name': 'Guest User',
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': self.company_id,
        })
        c1 = self.currency_obj.create({
            'code': 'C1',
            'symbol': 'C1',
            'name': 'Currency 1',
        })
        c2 = self.currency_obj.create({
            'code': 'C2',
            'symbol': 'C2',
            'name': 'Currency 2',
        })
        self.lang_currency = self.currency_obj.create({
            'code': 'C3',
            'symbol': 'C3',
            'name': 'Currency 3',
        })
        self.currency_obj.create({
            'code': 'C4',
            'symbol': 'C4',
            'name': 'Currency 4',
        })
        self.website_currency_ids = [c1, c2]
        url_map_id, = self.url_map_obj.search([], limit=1)
        self.en_us_id, = self.language_obj.search([('code', '=', 'en_US')])
        self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': self.company_id,
            'application_user': USER,
            'default_language': self.en_us_id,
            'guest_user': self.guest_user_id,
            'currencies': [('set', self.website_currency_ids)],
        })

    def get_template_source(self, name):
        """
        Return templates
        """
        templates = {
            'localhost/home.jinja': '{{ request.nereid_currency.id }}',
        }
        return templates.get(name)

    def test_0010_currency_from_company(self):
        """
        Do not set a currency for the language, and the failover of
        picking currency from company should work.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/en_US/')
                self.assertEqual(rv.status_code, 200)

            self.assertEqual(int(rv.data), self.company.currency.id)

    def test_0020_currency_from_language(self):
        """
        Set the currency for the language and check if the currency
        in the request is correct
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            self.language_obj.write(
                self.en_us_id, {'default_currency': self.lang_currency}
            )
            with app.test_client() as c:
                rv = c.get('/en_US/')
                self.assertEqual(rv.status_code, 200)

            self.assertEqual(int(rv.data), self.lang_currency)

def suite():
    "Currency test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency)
        )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
