#!/usr/bin/env python
"""

    Test the currency

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
from ast import literal_eval
import unittest2 as unittest

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
from trytond.modules import register_classes
register_classes()

from nereid.testing import testing_proxy, TestCase
from trytond.transaction import Transaction


class TestCurrency(TestCase):
    """Test Currency"""

    @classmethod
    def setUpClass(cls):
        super(TestCurrency, cls).setUpClass()
        testing_proxy.install_module('nereid')
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            company = testing_proxy.create_company('Test Company')
            cls.guest_user = testing_proxy.create_guest_user(company=company)
            cls.site = testing_proxy.create_site(
                'localhost',
                application_user = 1, guest_user = cls.guest_user
            )
            testing_proxy.create_template(
                'home.jinja', 
                '{{request.nereid_website.get_currencies()|safe}}',
                cls.site)
            txn.cursor.commit()

    def get_app(self):
        return testing_proxy.make_app(
            SITE='localhost', 
            GUEST_USER=self.guest_user)

    def setUp(self):
        self.currency_obj = testing_proxy.pool.get('currency.currency')
        self.site_obj = testing_proxy.pool.get('nereid.website')

    def test_0010_get_currencies(self):
        """Test if currencies are returned
        Expected: Empty list
        """
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/')
            self.assertEqual(literal_eval(rv.data), [])

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            currency_ids = self.currency_obj.search([], limit=5)
            self.site_obj.write(
                self.site, {'currencies': [('set', currency_ids)]}
            )
            txn.cursor.commit()

        with app.test_client() as c:
            rv = c.get('/en_US/')
            self.assertEqual(len(literal_eval(rv.data)), 5)

    def test_0020_set_invalid_currency(self):
        """Set invalid currency and assert 403"""
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/')
            data = literal_eval(rv.data)
            allowed_currencies = [c['id'] for c in data]

        with Transaction().start(testing_proxy.db_name, 1, None):
            invalid_id, = self.currency_obj.search(
                [('id', 'not in', allowed_currencies)], limit=1)

        with app.test_client() as c:
            rv = c.post('/en_US/set_currency', data={'currency': invalid_id})
            self.assertEqual(rv.status_code, 403)

    def test_0030_set_currency_post(self):
        """Set currency on POST and assert 302"""
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/')
            data = literal_eval(rv.data)
            allowed_currencies = [each['id'] for each in data]
            rv = c.post(
                '/en_US/set_currency', 
                data={'currency': allowed_currencies[0]}
            )
            self.assertEqual(rv.status_code, 302)

    def test_0040_set_currency_get(self):
        """Set currency on GET and assert 302"""
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/')
            data = literal_eval(rv.data)
            allowed_currencies = [each['id'] for each in data]
            rv = c.get(
                '/en_US/set_currency?currency=%s&next=/next' % (
                    allowed_currencies[0],)
            )
            self.assertEqual(rv.status_code, 302)
            self.assertEqual(rv.location, 'http://localhost/next')


def suite():
    "Currency test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
