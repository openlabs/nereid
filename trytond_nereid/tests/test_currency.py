#!/usr/bin/env python
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
from decimal import Decimal

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
        self.nereid_website_locale_obj = POOL.get('nereid.website.locale')
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
        usd, = self.currency_obj.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
            'rates': [('create', [{'rate': Decimal('1')}])],
        }])
        eur, = self.currency_obj.create([{
            'name': 'Euro',
            'code': 'EUR',
            'symbol': 'E',
            'rates': [('create', [{'rate': Decimal('2')}])],
        }])
        self.party, = self.party_obj.create([{
            'name': 'Openlabs',
        }])
        self.company, = self.company_obj.create([{
            'currency': usd,
            'party': self.party,
        }])
        self.guest_party, = self.party_obj.create([{
            'name': 'Guest User',
        }])
        self.guest_user, = self.nereid_user_obj.create([{
            'party': self.guest_party,
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': self.company.id,
        }])
        c1, = self.currency_obj.create([{
            'code': 'C1',
            'symbol': 'C1',
            'name': 'Currency 1',
            'rates': [('create', [{'rate': Decimal('10')}])],

        }])
        c2, = self.currency_obj.create([{
            'code': 'C2',
            'symbol': 'C2',
            'name': 'Currency 2',
            'rates': [('create', [{'rate': Decimal('20')}])],
        }])
        self.lang_currency, = self.currency_obj.create([{
            'code': 'C3',
            'symbol': 'C3',
            'name': 'Currency 3',
            'rates': [('create', [{'rate': Decimal('30')}])],
        }])
        self.currency_obj.create([{
            'code': 'C4',
            'symbol': 'C4',
            'name': 'Currency 4',
            'rates': [('create', [{'rate': Decimal('40')}])],
        }])
        self.website_currencies = [c1, c2]
        url_map, = self.url_map_obj.search([], limit=1)
        self.en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.es_es, = self.language_obj.search([('code', '=', 'es_ES')])
        self.usd, = self.currency_obj.search([('code', '=', 'USD')])
        self.eur, = self.currency_obj.search([('code', '=', 'EUR')])
        locale_en_us, locale_es_es = self.nereid_website_locale_obj.create([{
            'code': 'en_US',
            'language': self.en_us,
            'currency': self.usd,
        }, {
            'code': 'es_ES',
            'language': self.es_es,
            'currency': self.eur,
        }])
        self.nereid_website_obj.create([{
            'name': 'localhost',
            'url_map': url_map,
            'company': self.company,
            'application_user': USER,
            'default_locale': locale_en_us.id,
            'locales': [('add', [locale_en_us.id, locale_es_es.id])],
            'guest_user': self.guest_user.id,
            'currencies': [('set', self.website_currencies)],
        }])
        self.templates = {
            'home.jinja': '{{ request.nereid_currency.id }}',
        }

    def get_template_source(self, name):
        """
        Return templates
        """
        return self.templates.get(name)

    def test_0010_currency_from_default_locale(self):
        """
        Do not set a currency for the language, and the fail over of
        picking currency from default locale.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/en_us/')
                self.assertEqual(rv.status_code, 200)

            self.assertEqual(int(rv.data), self.usd.id)

            with app.test_request_context('/en_us/'):
                self.assertEqual(
                    self.currency_obj.convert(Decimal('100')), Decimal('100')
                )

    def test_0020_currency_from_locale(self):
        """
        Test and ensure that the currency is based on the locale
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/en_US/')
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(int(rv.data), int(self.usd.id))

                rv = c.get('/es_ES/')
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(int(rv.data), int(self.eur.id))

            with app.test_request_context('/en_US/'):
                self.assertEqual(
                    self.currency_obj.convert(Decimal('100')), Decimal('100')
                )

            with app.test_request_context('/es_ES/'):
                self.assertEqual(
                    self.currency_obj.convert(Decimal('100')), Decimal('200')
                )


def suite():
    "Currency test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
