# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from nereid.testing import NereidTestCase


class TestRouting(NereidTestCase):
    'Test URL Routing'

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid')

        self.nereid_website_obj = POOL.get('nereid.website')
        self.locale_obj = POOL.get('nereid.website.locale')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.url_map_obj = POOL.get('nereid.url_map')
        self.company_obj = POOL.get('company.company')
        self.language_obj = POOL.get('ir.lang')
        self.currency_obj = POOL.get('currency.currency')
        self.country_obj = POOL.get('country.country')
        self.subdivision_obj = POOL.get('country.subdivision')
        self.party_obj = POOL.get('party.party')

        self.templates = {
            'home.jinja': '{{ Transaction().language }}',
        }

    def setup_defaults(self):
        """
        Setup the defaults
        """
        self.usd, self.eur = self.currency_obj.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }, {
            'name': 'Euro',
            'code': 'EUR',
            'symbol': 'E',
            'rates': [('create', [{'rate': Decimal('2')}])],
        }])
        self.party, = self.party_obj.create([{
            'name': 'Openlabs',
        }])
        self.company, = self.company_obj.create([{
            'party': self.party,
            'currency': self.usd,
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
        party, = self.party_obj.create([{
            'name': 'Registered User',
        }])
        self.registered_user, = self.nereid_user_obj.create([{
            'party': party,
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': self.company,
        }])

        url_map_id, = self.url_map_obj.search([], limit=1)

        self.en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.es_es, = self.language_obj.search([('code', '=', 'es_ES')])
        self.locale_en_us, self.locale_es_es = self.locale_obj.create([{
            'code': 'en_US',
            'language': self.en_us,
            'currency': self.usd,
        }, {
            'code': 'es_ES',
            'language': self.es_es,
            'currency': self.eur,
        }])

        self.nereid_website, = self.nereid_website_obj.create([{
            'name': 'localhost',
            'url_map': url_map_id,
            'company': self.company,
            'application_user': USER,
            'default_locale': self.locale_en_us,
            'locales': [('add', [self.locale_en_us.id, self.locale_es_es.id])],
            'guest_user': self.guest_user,
        }])

    def get_template_source(self, name):
        """
        Return templates
        """
        return self.templates.get(name)

    def get_app(self):
        """
        Inject transaction into the template context for the home template
        """
        app = super(TestRouting, self).get_app()
        app.jinja_env.globals['Transaction'] = Transaction
        return app

    def test_0010_home_with_locales(self):
        """
        When accessing / for website with locales defined, there should be a
        redirect to the /locale
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/')
                self.assertEqual(response.status_code, 301)
                self.assertEqual(
                    response.location,
                    'http://localhost/%s' % self.locale_en_us.code
                )

            # Change the default locale to es_ES and then check
            self.nereid_website.default_locale = self.locale_es_es
            self.nereid_website.save()
            self.nereid_website.clear_url_adapter_cache()

            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/')
                self.assertEqual(response.status_code, 301)
                self.assertEqual(
                    response.location,
                    'http://localhost/%s' % self.locale_es_es.code
                )

    def test_0020_home_without_locales(self):
        """
        When accessed without locales the site should return 200 on /
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            # unset the locales
            self.nereid_website.locales = []
            self.nereid_website.save()

            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, 'en_US')

    def test_0030_lang_context_with_locale(self):
        """
        Test that the language available in the context is the right one
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/en_US/')
                self.assertEqual(response.data, 'en_US')

            with app.test_client() as c:
                response = c.get('/es_ES/')
                self.assertEqual(response.data, 'es_ES')

    def test_0040_lang_context_without_locale(self):
        """
        Test that the language available in the context is the right one
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            self.nereid_website.locales = []
            self.nereid_website.save()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/')
                self.assertEqual(response.data, 'en_US')

            # Change the default locale to es_ES and then check
            self.nereid_website.default_locale = self.locale_es_es
            self.nereid_website.save()

            with app.test_client() as c:
                response = c.get('/')
                self.assertEqual(response.data, 'es_ES')

    def test_0050_invalid_active_id_url(self):
        """
        Test that the url if 404 if record for active_id doesn't exist
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            self.nereid_website.locales = []
            self.nereid_website.save()
            app = self.get_app()
            country, = self.country_obj.create([{
                'name': 'India',
                'code': 'IN'
            }])

            with app.test_client() as c:
                response = c.get('/countries/%d/subdivisions' % country.id)
                self.assertEqual(response.status_code, 200)

                response = c.get('/countries/6/subdivisions')  # Invalid record
                self.assertEqual(response.status_code, 404)


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestRouting)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
