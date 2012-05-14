# -*- coding: utf-8 -*-
"""
    nereid.test

    Test the configuration features for nereid

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import unittest2 as unittest

from minimock import Mock
import smtplib
smtplib.SMTP = Mock('smtplib.SMTP')
smtplib.SMTP.mock_returns = Mock('smtp_connection')

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
CONFIG.options['data_path'] = '/tmp/temp_tryton_data/'
CONFIG['smtp_server'] = 'smtp.gmail.com'
CONFIG['smtp_user'] = 'test@xyz.com'
CONFIG['smtp_password'] = 'testpassword'
CONFIG['smtp_port'] = 587
CONFIG['smtp_tls'] = True
from trytond.modules import register_classes
register_classes()

from nereid.testing import testing_proxy, TestCase
from trytond.transaction import Transaction

GUEST_EMAIL = 'guest@example.com'
NEW_USER = 'new.test@example.com'
NEW_PASS = 'password'

class TestAddress(TestCase):
    'Test Address'

    @classmethod
    def setUpClass(cls):
        super(TestAddress, cls).setUpClass()
        testing_proxy.install_module('nereid')

        country_obj = testing_proxy.pool.get('country.country')

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            company = testing_proxy.create_company('Test Company')
            testing_proxy.set_company_for_user(1, company)

            cls.guest_user = testing_proxy.create_guest_user(company=company)
            cls.regd_user_id = testing_proxy.create_user_party(
                'Registered User', 'email@example.com', 'password', company
            )

            cls.available_countries = country_obj.search([], limit=5)
            cls.site = testing_proxy.create_site(
                'localhost',
                countries = [('set', cls.available_countries)],
                application_user = 1, guest_user = cls.guest_user
                )

            testing_proxy.create_template(
                'home.jinja',
                '{{get_flashed_messages()}}', cls.site)
            testing_proxy.create_template(
                'login.jinja',
                '{{ login_form.errors }} {{get_flashed_messages()}}', cls.site)
            testing_proxy.create_template(
                'registration.jinja',
                '{{ form.errors }} {{get_flashed_messages()}}', cls.site)

            testing_proxy.create_template(
                'reset-password.jinja', '', cls.site)
            testing_proxy.create_template(
                'change-password.jinja',
                '{{ change_password_form.errors }}', cls.site)
            testing_proxy.create_template(
                'address-edit.jinja',
                'Address Edit {{ form.errors }}', cls.site)
            testing_proxy.create_template(
                'address.jinja', '', cls.site)
            testing_proxy.create_template(
                'account.jinja', '', cls.site)

            txn.cursor.commit()

    def get_app(self, **options):
        options.update({
            'SITE': 'testsite.com',
            })
        return testing_proxy.make_app(**options)

    def setUp(self):
        self.nereid_user_obj = testing_proxy.pool.get('nereid.user')
        self.address_obj = testing_proxy.pool.get('party.address')
        self.country_obj = testing_proxy.pool.get('country.country')
        self.subdivision_obj = testing_proxy.pool.get('country.subdivision')
        self.website_obj = testing_proxy.pool.get('nereid.website')
        self.contact_mech_obj = testing_proxy.pool.get(
            'party.contact_mechanism'
        )

    def test_0010_add_address(self):
        """
        Add an address for the user
        """
        app = self.get_app()

        with app.test_client() as c:
            # Without login, redirect to login
            data = {
                'name': 'New Test Registered User',
                'email': 'new.test@example.com',
                'password': 'password',
                'confirm': 'password',
            }
            response = c.post('/en_US/registration', data=data)
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None) as txn:
            nereid_user_id, = self.nereid_user_obj.search([
                ('email', '=', 'new.test@example.com')
            ])
            self.nereid_user_obj.write(
                nereid_user_id, {'activation_code': None}
            ) # Force activate the user
            new_user = self.nereid_user_obj.browse(nereid_user_id)

            # When a party is created an address record is also created
            address_id, = self.address_obj.search(
                [('party', '=', new_user.party.id)]
            )

            # Create a new address data that could be sent to server
            country = self.available_countries[0]
            subdivision = self.country_obj.browse(country).subdivisions[0].id
            address_data = {
                'name': 'Name',
                'street': 'Street',
                'streetbis': 'StreetBis',
                'zip': 'zip',
                'city': 'City',
                'country': country,
                'subdivision': subdivision,
                }
            txn.cursor.commit()

        with app.test_client() as c:
            # Login and list addresses
            response = c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'}
            )

            self.assertEqual(response.status_code, 302)
            response = c.get('/en_US/edit-address/%d' % address_id)
            self.assertEqual(response.status_code, 200)

            # POST and a new address must be created
            response = c.post(
                '/en_US/edit-address/%d' % address_id,
                data=address_data
            )
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            new_user = self.nereid_user_obj.browse(nereid_user_id)
            for address in new_user.party.addresses:
                address_from_db = self.address_obj.read(
                    address.id, address_data.keys()
                )
                address_from_db.pop('id')
                if address_from_db == address_data:
                    break
            else:
                self.fail("Address record data mismatch")

    def test_0060_edit_address(self):
        "Edit the address of a user"
        app = self.get_app()

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            new_user_id, = self.nereid_user_obj.search(
                [('email', '=', 'new.test@example.com')]
            )
            new_user = self.nereid_user_obj.browse(new_user_id)
            address_id, = self.address_obj.search(
                [('party', '=', new_user.party.id)], limit=1
            )

        with app.test_client() as c:
            c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'})

            # On submitting an empty form the page should load back
            response = c.get('/en_US/edit-address/%d' % address_id)
            self.assertEqual(response.status_code, 200)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            website_id = self.website_obj.search([])[0]
            website = self.website_obj.browse(website_id)
            country = website.countries[1]
            subdivision = country.subdivisions[2]
            address_data = {
                'name': 'New test User 2',
                'street': 'New Street 2',
                'streetbis': 'New Street2 2',
                'zip': '678GHB',
                'city': 'Test City 2',
                'country': country.id,
                'subdivision': subdivision.id,
                }

        with app.test_client() as c:
            c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'})
            response = c.post(
                '/en_US/edit-address/%d' % address_id,
                data=address_data
            )
            self.assertEqual(response.status_code, 302)

            response = c.post('/en_US/edit-address/%d' % 0, data=address_data)
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            address = self.address_obj.read(address_id, address_data.keys())
            address.pop('id')
            self.assertEqual(address, address_data)

    def test_0070_view_address(self):
        app = self.get_app()
        with app.test_client() as c:
            c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'})
            response = c.get('/en_US/view-address')
            self.assertEqual(response.status_code, 200)

    def test_0080_login(self):
        "Check whether a registered user can login"
        app = self.get_app()
        with app.test_client() as c:

            # Correct entries will redirect to home or some other page
            response = c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'})
            self.assertEqual(response.status_code, 302)

            # Wrong entries will render the login page again
            response = c.post('/en_US/login', 
                data={
                    'email': 'new.test@example.com', 
                    'password': 'wrong-password'})
            self.assertEqual(response.status_code, 200)

    def test_0090_logout(self):
        "Check whether a logged in user can logout"
        app = self.get_app()
        with app.test_client() as c:
            c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'})

            response = c.get('/en_US/logout')
            self.assertEqual(response.status_code, 302)

    def test_0100_account(self):
        "Check the display the account details of a user"
        app = self.get_app()
        with app.test_client() as c:
            c.post('/en_US/login', 
                data={'email': 'new.test@example.com', 'password': 'password'})

            response = c.get('/en_US/account')
            self.assertEqual(response.status_code, 200)

    def test_0110_country_list(self):
        "Check if the website countries are there in country list"
        app = self.get_app()
        with app.test_client() as c:
            response = c.get('/en_US/countries')
            self.assertEqual(len(eval(response.data)['result']), 5)

    def test_0120_subdivision_list(self):
        "Check if a country has states"
        with Transaction().start(testing_proxy.db_name, testing_proxy.user, None):
            website_id = self.website_obj.search([])[0]
            website = self.website_obj.browse(website_id)
            country = website.countries[1]
        app = self.get_app()
        with app.test_client() as c:
            response = c.get('/en_US/subdivisions?country=%d' % country)
            self.assertEqual(not(len(eval(response.data)['result'])), 0)
            
    def test_0130_addtional_details(self):
        "Test whether the additional details work"
        address_additional = testing_proxy.pool.get('address.additional_details')
        with Transaction().start(testing_proxy.db_name, testing_proxy.user, None):
            any_user_id = self.address_obj.search([])[0]
            address_additional.create({
                'type': 'dob',
                'value': '1/1/2000',
                'sequence': 10,
                'address': any_user_id})
            any_user = self.address_obj.browse(any_user_id)
            self.assertEqual(any_user.additional_details[0].value, '1/1/2000')
            

def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAddress)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
