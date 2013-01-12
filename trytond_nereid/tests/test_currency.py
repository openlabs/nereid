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
        self.currency_obj.create({
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
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': self.company_id,
            'application_user': USER,
            'default_language': en_us,
            'guest_user': self.guest_user_id,
            'currencies': [('set', self.website_currency_ids)],
        })

    def get_template_source(self, name):
        """
        Return templates
        """
        templates = {
            'localhost/home.jinja': '{{get_flashed_messages()}}',
        }
        return templates.get(name)

    def test_0010_set_not_allowed_currency(self):
        """
        Set not allowed currency and assert 403
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            invalid_id, = self.currency_obj.search(
                [('id', 'not in', self.website_currency_ids)], limit=1
            )

            with app.test_client() as c:
                rv = c.post('/en_US/set_currency', data={'currency': invalid_id})
                self.assertEqual(rv.status_code, 403)

    def test_0020_set_currency_post(self):
        """
        Set currency on POST and assert 302
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.post(
                    '/en_US/set_currency',
                    data={'currency': self.website_currency_ids[0]}
                )
                self.assertEqual(rv.status_code, 302)

    def test_0030_set_currency_get(self):
        """
        Set currency on GET and assert 302
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get(
                    '/en_US/set_currency?currency=%s&next=/next' % (
                        self.website_currency_ids[0]
                    )
                )
                self.assertEqual(rv.status_code, 302)
                self.assertEqual(rv.location, 'http://localhost/next')


def suite():
    "Currency test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency)
        )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
