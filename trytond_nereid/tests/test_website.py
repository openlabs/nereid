# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import json

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from nereid.testing import NereidTestCase


class TestWebsite(NereidTestCase):
    'Test Website'

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid')

        self.NereidWebsite = POOL.get('nereid.website')
        self.NereidWebsiteLocale = POOL.get('nereid.website.locale')
        self.NereidPermission = POOL.get('nereid.permission')
        self.NereidUser = POOL.get('nereid.user')
        self.Company = POOL.get('company.company')
        self.Currency = POOL.get('currency.currency')
        self.Language = POOL.get('ir.lang')
        self.Party = POOL.get('party.party')

    def setup_defaults(self):
        """
        Setup the defaults
        """
        usd, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])
        self.party, = self.Party.create([{
            'name': 'Openlabs',
        }])
        self.company, = self.Company.create([{
            'party': self.party,
            'currency': usd,
        }])

        en_us, = self.Language.search([('code', '=', 'en_US')])
        currency, = self.Currency.search([('code', '=', 'USD')])
        locale, = self.NereidWebsiteLocale.create([{
            'code': 'en_US',
            'language': en_us,
            'currency': currency,
        }])
        self.NereidWebsite.create([{
            'name': 'localhost',
            'company': self.company,
            'application_user': USER,
            'default_locale': locale,
        }])

    def test_0010_user_status(self):
        """
        Test that user status returns jsonified object on POST
        request.
        """
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/user_status')
                self.assertEqual(rv.status_code, 200)

                rv = c.post('/user_status')
                data = json.loads(rv.data)

                self.assertEqual(data['status']['logged_id'], False)
                self.assertEqual(data['status']['messages'], [])


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestWebsite)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
