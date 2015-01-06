# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import json
import unittest

import pycountry
from mock import patch
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from trytond.config import config
from nereid.testing import NereidTestCase

config.set('email', 'from', 'from@xyz.com')


class TestAddress(NereidTestCase):
    'Test Address'

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid')

        self.nereid_website_obj = POOL.get('nereid.website')
        self.nereid_website_locale_obj = POOL.get('nereid.website.locale')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.company_obj = POOL.get('company.company')
        self.currency_obj = POOL.get('currency.currency')
        self.language_obj = POOL.get('ir.lang')
        self.country_obj = POOL.get('country.country')
        self.subdivision_obj = POOL.get('country.subdivision')
        self.party_obj = POOL.get('party.party')
        self.address_obj = POOL.get('party.address')
        self.contact_mech_obj = POOL.get('party.contact_mechanism')

        self.templates = {
            'home.jinja':
            "{{ get_using_xml_id('ir', 'lang_en').name }}",
            'login.jinja':
            '{{ login_form.errors }} {{get_flashed_messages()}}',
            'registration.jinja':
            '{{ form.errors }} {{get_flashed_messages()}}',
            'reset-password.jinja': '',
            'change-password.jinja':
            '{{ change_password_form.errors }}',
            'address-edit.jinja':
            'Address Edit {% if address %}ID:{{ address.id }}{% endif %}'
            '{{ form.errors }}',
            'address.jinja': '',
            'account.jinja': '',
            'emails/activation-text.jinja': 'activation-email-text',
            'emails/activation-html.jinja': 'activation-email-html',
            'emails/reset-text.jinja': 'reset-email-text',
            'emails/reset-html.jinja': 'reset-email-html',
        }

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
            country_id, = self.country_obj.create([{
                'name': country.name,
                'code': country.alpha2,
            }])
            try:
                divisions = pycountry.subdivisions.get(
                    country_code=country.alpha2
                )
            except KeyError:
                pass
            else:
                self.subdivision_obj.create([{
                    'country': country_id,
                    'name': subdivision.name,
                    'code': subdivision.code,
                    'type': subdivision.type.lower(),
                } for subdivision in list(divisions)[0:count]])

    def setup_defaults(self):
        """
        Setup the defaults
        """
        usd, = self.currency_obj.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])
        self.party, = self.party_obj.create([{
            'name': 'Openlabs',
        }])
        self.company, = self.company_obj.create([{
            'party': self.party,
            'currency': usd,
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

        self.create_countries()
        self.available_countries = self.country_obj.search([], limit=5)

        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        currency, = self.currency_obj.search([('code', '=', 'USD')])
        locale, = self.nereid_website_locale_obj.create([{
            'code': 'en_US',
            'language': en_us,
            'currency': currency,
        }])
        self.nereid_website_obj.create([{
            'name': 'localhost',
            'company': self.company,
            'application_user': USER,
            'default_locale': locale,
            'locales': [('add', [locale.id])],
            'countries': [('add', self.available_countries)],
        }])

    def get_template_source(self, name):
        """
        Return templates
        """
        return self.templates.get(name)

    # XXX: Due for deprecation in 3.2.X
    def test_0010_add_address(self):
        """
        Add an address for the user
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            registered_user = self.registered_user

            address_data = {
                'name': 'Name',
                'street': 'Street',
                'streetbis': 'StreetBis',
                'zip': 'zip',
                'city': 'City',
                'email': 'email@example.com',
                'phone': '1234567890',
                'country': self.available_countries[0].id,
                'subdivision': self.country_obj(
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
                self.assertEqual(response.status_code, 302)  # Login success

                self.assertEqual(len(registered_user.party.addresses), 0)

                # POST and a new address must be created
                response = c.post('/en_US/save-new-address', data=address_data)
                self.assertEqual(response.status_code, 302)

                # Re browse the record
                registered_user = self.nereid_user_obj(
                    self.registered_user.id
                )
                # Check if the user has one addresses now
                self.assertEqual(len(registered_user.party.addresses), 1)

                address, = registered_user.party.addresses
                self.assertEqual(address.name, address_data['name'])
                self.assertEqual(address.street, address_data['street'])
                self.assertEqual(address.streetbis, address_data['streetbis'])
                self.assertEqual(address.zip, address_data['zip'])
                self.assertEqual(address.city, address_data['city'])
                self.assertEqual(address.party.email, address_data['email'])
                self.assertEqual(address.party.phone, address_data['phone'])
                self.assertEqual(address.country.id, address_data['country'])
                self.assertEqual(
                    address.subdivision.id, address_data['subdivision']
                )

    def test_0015_add_address(self):
        """
        Add an address for the user.

        The create_address method was introduced in 3.0.3.0
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            registered_user = self.registered_user

            address_data = {
                'name': 'Name',
                'street': 'Street',
                'streetbis': 'StreetBis',
                'zip': 'zip',
                'city': 'City',
                'email': 'email@example.com',
                'phone': '1234567890',
                'country': self.available_countries[0].id,
                'subdivision': self.country_obj(
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
                self.assertEqual(response.status_code, 302)  # Login success

                self.assertEqual(len(registered_user.party.addresses), 0)

                # POST and a new address must be created
                response = c.post('/en_US/create-address', data=address_data)
                self.assertEqual(response.status_code, 302)

                # Re browse the record
                registered_user = self.nereid_user_obj(
                    self.registered_user.id
                )
                # Check if the user has two addresses now
                self.assertEqual(len(registered_user.party.addresses), 1)

                address, = registered_user.party.addresses
                self.assertEqual(address.name, address_data['name'])
                self.assertEqual(address.street, address_data['street'])
                self.assertEqual(address.streetbis, address_data['streetbis'])
                self.assertEqual(address.zip, address_data['zip'])
                self.assertEqual(address.city, address_data['city'])
                self.assertEqual(address.party.email, address_data['email'])
                self.assertEqual(address.party.phone, address_data['phone'])
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

            registered_user = self.registered_user
            address_data = {
                'name': 'Name',
                'street': 'Street',
                'streetbis': 'StreetBis',
                'zip': 'zip',
                'city': 'City',
                'email': 'email@example.com',
                'phone': '1234567890',
                'country': self.available_countries[0].id,
                'subdivision': self.country_obj(
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
                self.assertEqual(response.status_code, 302)  # Login success

                # Create an address that can be edited
                self.assertEqual(len(registered_user.party.addresses), 0)
                existing_address, = self.address_obj.create([{
                    'party': registered_user.party.id,
                }])

                response = c.get(
                    '/en_US/edit-address/%d' % existing_address.id
                )
                self.assertTrue('ID:%s' % existing_address.id in response.data)

                # POST to the existing address must updatethe existing address
                response = c.post(
                    '/en_US/edit-address/%d' % existing_address.id,
                    data=address_data
                )
                self.assertEqual(response.status_code, 302)

                # Assert that the user has only 1 address
                self.assertEqual(len(registered_user.party.addresses), 1)

                address = self.address_obj(existing_address.id)
                self.assertEqual(address.name, address_data['name'])
                self.assertEqual(address.street, address_data['street'])
                self.assertEqual(address.streetbis, address_data['streetbis'])
                self.assertEqual(address.zip, address_data['zip'])
                self.assertEqual(address.city, address_data['city'])
                self.assertEqual(address.party.email, address_data['email'])
                self.assertEqual(address.party.phone, address_data['phone'])
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
                self.assertEqual(response.status_code, 302)  # Login success

            with app.test_client() as c:
                response = c.get('/en_US/view-address')
                self.assertEqual(response.status_code, 302)  # Redir to login

    def test_0040_country_list(self):
        """
        Check if the website countries are there in country list
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()
            with app.test_client() as c:
                response = c.get('/en_US/countries')
                self.assertEqual(response.status_code, 200)  # Login success
                self.assertEqual(len(json.loads(response.data)['result']), 5)

    def test_0050_subdivision_list(self):
        """
        Check if a country's subdivisions are returned
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            # Set in :meth:`setup_defaults`
            countries = filter(
                lambda c: c.subdivisions, self.available_countries
            )
            country = countries[0]

            with app.test_client() as c:
                response = c.get('/en_US/subdivisions?country=%d' % country)
                self.assertNotEqual(
                    len(json.loads(response.data)['result']), 0
                )

    def test_0060_contact_mechanism(self):
        """
        Add an contact mechanism for the user.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            contact_data = {
                'party': self.registered_user.party.id,
                'type': 'irc',
                'value': 'Value',
                'comment': 'Comment',
            }

            with app.test_client() as c:
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': 'email@example.com',
                        'password': 'password',
                    }
                )
                self.assertEqual(response.status_code, 302)  # Login success

                # Add a new contact mechanism
                response = c.post(
                    '/en_US/contact-mechanisms/add', data=contact_data
                )
                self.assertEqual(response.status_code, 302)

                self.assertEqual(
                    len(self.registered_user.party.contact_mechanisms), 1
                )
                self.assertEqual(contact_data['type'], 'irc')
                self.assertEqual(contact_data['value'], 'Value')
                self.assertEqual(contact_data['comment'], 'Comment')

    def test_0070_test_get_using_xml_id(self):
        """
        Tests context processor get_using_xml_id.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/en_US/')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, 'English')

    def test_0080_remove_address(self):
        """
        Test for making address inactive when user wants to remove address.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            registered_user = self.registered_user

            with app.test_client() as c:
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': 'email@example.com',
                        'password': 'password',
                    }
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(len(registered_user.party.addresses), 0)
                self.address_obj.create([{
                    'party': registered_user.party.id,
                }])

                c.post(
                    '/en_US/remove-address/%d' %
                    (registered_user.party.addresses[0].id, )
                )
                self.assertEqual(len(registered_user.party.addresses), 0)

    def test_0090_remove_address_by_unauthorized_user(self):
        """
        Test if registered user can remove the address of another registered
        user.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party1, = self.party_obj.create([{
                'name': 'TestParty',
            }])

            # Creating new_user
            new_user, = self.nereid_user_obj.create([{
                'party': party1,
                'display_name': 'Test User',
                'email': 'registered-user@example.com',
                'password': 'password',
                'company': self.company,
            }])
            # Login from registered_user.
            with app.test_client() as c:
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': 'email@example.com',
                        'password': 'password',
                    }
                )
                self.assertEqual(response.status_code, 302)

                # check for addresses in new_user address book.
                self.address_obj.create([{
                    'party': new_user.party.id,
                }])
                self.assertEqual(len(new_user.party.addresses), 1)

                # registered_user trying to remove address of new_user
                rv = c.post(
                    '/en_US/remove-address/%d' %
                    (new_user.party.addresses[0].id, )
                )
                self.assertEqual(rv.status_code, 403)


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAddress)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
