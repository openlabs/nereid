# -*- coding: utf-8 -*-
"""

    Test the configuration features for nereid

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import json
import unittest

import pycountry
from mock import patch
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from trytond.config import CONFIG
from nereid.testing import NereidTestCase

CONFIG['smtp_server'] = 'smtpserver'
CONFIG['smtp_user'] = 'test@xyz.com'
CONFIG['smtp_password'] = 'testpassword'
CONFIG['smtp_port'] = 587
CONFIG['smtp_tls'] = True
CONFIG['smtp_from'] = 'from@xyz.com'


class TestAddress(NereidTestCase):
    'Test Address'

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid')

        self.nereid_website_obj = POOL.get('nereid.website')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.url_map_obj = POOL.get('nereid.url_map')
        self.company_obj = POOL.get('company.company')
        self.currency_obj = POOL.get('currency.currency')
        self.language_obj = POOL.get('ir.lang')
        self.country_obj = POOL.get('country.country')
        self.subdivision_obj = POOL.get('country.subdivision')
        self.party_obj = POOL.get('party.party')
        self.address_obj = POOL.get('party.address')
        self.contact_mech_obj = POOL.get('party.contact_mechanism')

        # Patch SMTP Lib
        self.smtplib_patcher = patch('smtplib.SMTP')
        self.PatchedSMTP = self.smtplib_patcher.start()

    def tearDown(self):
        # Unpatch SMTP Lib
        self.smtplib_patcher.stop()

    def create_countries(self, count=5):
        """
        Create some sample countries and subdivisions
        """
        for country in list(pycountry.countries)[0:count]:
            country_id = self.country_obj.create({
                'name': country.name,
                'code': country.alpha2,
            })
            try:
                divisions = pycountry.subdivisions.get(
                    country_code=country.alpha2
                )
            except KeyError:
                pass
            else:
                for subdivision in list(divisions)[0:count]:
                    self.subdivision_obj.create({
                        'country': country_id,
                        'name': subdivision.name,
                        'code': subdivision.code,
                        'type': subdivision.type.lower(),
                    })

    def setup_defaults(self):
        """
        Setup the defaults
        """
        usd = self.currency_obj.create({
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        })
        company_id = self.company_obj.create({
            'name': 'Openlabs',
            'currency': usd
        })
        guest_user = self.nereid_user_obj.create({
            'name': 'Guest User',
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': company_id,
        })
        self.registered_user_id = self.nereid_user_obj.create({
            'name': 'Registered User',
            'display_name': 'Registered User',
            'email': 'email@example.com',
            'password': 'password',
            'company': company_id,
        })

        self.create_countries()
        self.available_countries = self.country_obj.search([], limit=5)

        url_map_id, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': company_id,
            'application_user': USER,
            'default_language': en_us,
            'guest_user': guest_user,
            'countries': [('set', self.available_countries)],
        })

    def get_template_source(self, name):
        """
        Return templates
        """
        templates = {
            'localhost/home.jinja': '{{get_flashed_messages()}}',
            'localhost/login.jinja':
                    '{{ login_form.errors }} {{get_flashed_messages()}}',
            'localhost/registration.jinja':
                    '{{ form.errors }} {{get_flashed_messages()}}',
            'localhost/reset-password.jinja': '',
            'localhost/change-password.jinja':
                    '{{ change_password_form.errors }}',
            'localhost/address-edit.jinja': 'Address Edit {{ form.errors }}',
            'localhost/address.jinja': '',
            'localhost/account.jinja': '',
            'localhost/emails/activation-text.jinja': 'activation-email-text',
            'localhost/emails/activation-html.jinja': 'activation-email-html',
            'localhost/emails/reset-text.jinja': 'reset-email-text',
            'localhost/emails/reset-html.jinja': 'reset-email-html',
        }
        return templates.get(name)

    def test_0010_add_address(self):
        """
        Add an address for the user
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            registered_user = self.nereid_user_obj.browse(
                self.registered_user_id
            )
            address_data = {
                'name': 'Name',
                'street': 'Street',
                'streetbis': 'StreetBis',
                'zip': 'zip',
                'city': 'City',
                'country': self.available_countries[0],
                'subdivision': self.country_obj.browse(
                        self.available_countries[0]).subdivisions[0].id,
            }

            with app.test_client() as c:
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': 'email@example.com',
                        'password': 'password',
                    }
                )
                self.assertEqual(response.status_code, 302) # Login success

                # Assert that the user has only 1 address, which gets created
                # automatically with the party
                self.assertEqual(len(registered_user.party.addresses), 1)
                existing_address, = registered_user.party.addresses

                # POST and a new address must be created
                response = c.post('/en_US/save-new-address', data=address_data)
                self.assertEqual(response.status_code, 302)

                # Re browse the record
                registered_user = self.nereid_user_obj.browse(
                    self.registered_user_id
                )
                # Check if the user has two addresses now
                self.assertEqual(len(registered_user.party.addresses), 2)
                for address in registered_user.party.addresses:
                    if address != existing_address:
                        break
                else:
                    self.fail("New address not found")

                self.assertEqual(address.name, address_data['name'])
                self.assertEqual(address.street, address_data['street'])
                self.assertEqual(address.streetbis, address_data['streetbis'])
                self.assertEqual(address.zip, address_data['zip'])
                self.assertEqual(address.city, address_data['city'])
                self.assertEqual(address.country.id, address_data['country'])
                self.assertEqual(
                    address.subdivision.id, address_data['subdivision']
                )

    def test_0020_edit_address(self):
        """
        Edit an address for the user
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            registered_user = self.nereid_user_obj.browse(
                self.registered_user_id
            )
            address_data = {
                'name': 'Name',
                'street': 'Street',
                'streetbis': 'StreetBis',
                'zip': 'zip',
                'city': 'City',
                'country': self.available_countries[0],
                'subdivision': self.country_obj.browse(
                        self.available_countries[0]).subdivisions[0].id,
            }

            with app.test_client() as c:
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': 'email@example.com',
                        'password': 'password',
                    }
                )
                self.assertEqual(response.status_code, 302) # Login success

                # Assert that the user has only 1 address, which gets created
                # automatically with the party
                self.assertEqual(len(registered_user.party.addresses), 1)
                existing_address, = registered_user.party.addresses

                # POST to the existing address must updatethe existing address
                response = c.post(
                    '/en_US/edit-address/%d' % existing_address.id,
                    data=address_data
                )
                self.assertEqual(response.status_code, 302)

                # Assert that the user has only 1 address, which gets created
                # automatically with the party
                self.assertEqual(len(registered_user.party.addresses), 1)

                address = self.address_obj.browse(existing_address.id)
                self.assertEqual(address.name, address_data['name'])
                self.assertEqual(address.street, address_data['street'])
                self.assertEqual(address.streetbis, address_data['streetbis'])
                self.assertEqual(address.zip, address_data['zip'])
                self.assertEqual(address.city, address_data['city'])
                self.assertEqual(address.country.id, address_data['country'])
                self.assertEqual(
                    address.subdivision.id, address_data['subdivision']
                )

    def test_0030_view_addresses(self):
        """
        Display a list of all addresses
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': 'email@example.com',
                        'password': 'password',
                    }
                )
                self.assertEqual(response.status_code, 302) # Login success

            with app.test_client() as c:
                response = c.get('/en_US/view-address')
                self.assertEqual(response.status_code, 302) # Redir to login

    def test_0040_country_list(self):
        """
        Check if the website countries are there in country list
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()
            with app.test_client() as c:
                response = c.get('/en_US/countries')
                self.assertEqual(len(json.loads(response.data)['result']), 5)

    def test_0050_subdivision_list(self):
        """
        Check if a country's subdivisions are returned
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            # Set in :meth:`setup_defaults`
            country = self.available_countries[1]

            with app.test_client() as c:
                response = c.get('/en_US/subdivisions?country=%d' % country)
                self.assertNotEqual(
                    len(json.loads(response.data)['result']), 0
                )


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAddress)
        )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
