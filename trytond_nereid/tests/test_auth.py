#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

    Test the Auth layer

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import unittest

from mock import patch
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import CONFIG
from nereid.testing import NereidTestCase
from nereid import permissions_required
from werkzeug.exceptions import Forbidden

CONFIG['smtp_from'] = 'from@xyz.com'


class TestAuth(NereidTestCase):
    """
    Test Authentication Layer
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

        # Patch SMTP Lib
        self.smtplib_patcher = patch('smtplib.SMTP', autospec=True)
        self.PatchedSMTP = self.smtplib_patcher.start()
        self.mocked_smtp_instance = self.PatchedSMTP.return_value

    def tearDown(self):
        # Unpatch SMTP Lib
        self.smtplib_patcher.stop()

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

        url_map_id, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': self.company_id,
            'application_user': USER,
            'default_language': en_us,
            'guest_user': self.guest_user_id,
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
                    '''{{ change_password_form.errors }}
                    {{get_flashed_messages()}}''',
            'localhost/address-edit.jinja': 'Address Edit {{ form.errors }}',
            'localhost/address.jinja': '',
            'localhost/account.jinja': '',
            'localhost/emails/activation-text.jinja': 'activation-email-text',
            'localhost/emails/activation-html.jinja': 'activation-email-html',
            'localhost/emails/reset-text.jinja': 'reset-email-text',
            'localhost/emails/reset-html.jinja': 'reset-email-html',
        }
        return templates.get(name)

    def test_0005_mock_setup(self):
        assert get_smtp_server() is self.PatchedSMTP.return_value

    def test_0010_register(self):
        """
        Registration must create a new party
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/en_US/registration')
                self.assertEqual(response.status_code, 200) # GET Request

                data = {
                    'name': 'Registered User',
                    'email': 'regd_user@openlabs.co.in',
                    'password': 'password'
                }
                # Post with missing password
                response = c.post('/en_US/registration', data=data)
                self.assertEqual(response.status_code, 200) # Form rejected

                data['confirm'] = 'password'
                response = c.post('/en_US/registration', data=data)
                self.assertEqual(response.status_code, 302)

                self.assertEqual(
                    self.mocked_smtp_instance.sendmail.call_count, 1
                )
                self.assertEqual(
                    self.mocked_smtp_instance.sendmail.call_args[0][0],
                    CONFIG['smtp_from']
                )
                self.assertEqual(
                    self.mocked_smtp_instance.sendmail.call_args[0][1],
                    [data['email']]
                )

            self.assertEqual(
                self.party_obj.search(
                    [('name', '=', data['name'])], count=True
                ), 1
            )
            self.assertEqual(
                self.nereid_user_obj.search(
                    [('email', '=', data['email'])], count=True
                ), 1
            )

    def test_0020_activation(self):
        """
        Activation must happen before login is possible
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                data = {
                    'name': 'Registered User',
                    'email': 'regd_user@openlabs.co.in',
                    'password': 'password',
                    'confirm': 'password',
                }
                data['confirm'] = 'password'
                response = c.post('/en_US/registration', data=data)
                self.assertEqual(response.status_code, 302)

                regd_user_id, = self.nereid_user_obj.search(
                    [('email', '=', data['email'])]
                )
                registered_user = self.nereid_user_obj.browse(regd_user_id)
                self.assertTrue(registered_user.activation_code)

                # Login should fail since there is activation code
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': data['email'],
                        'password': data['password'],
                    }
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    "Your account has not been activated yet" in response.data
                )

                # Activate the account
                response = c.get('/en_US/activate-account/%s/%s' % (
                    registered_user.id, registered_user.activation_code
                    )
                )
                self.assertEqual(response.status_code, 302)
                registered_user = self.nereid_user_obj.browse(regd_user_id)

                # Activation code must be cleared
                self.assertFalse(registered_user.activation_code)

                # Login should work
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': data['email'],
                        'password': data['password'],
                    }
                )
                self.assertEqual(response.status_code, 302)

    def test_0030_change_password(self):
        """
        Check password changing functionality
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            data = {
                'name': 'Registered User',
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company_id,
            }
            self.nereid_user_obj.create(data.copy())

            with app.test_client() as c:
                # try the page without login
                response = c.get('/en_US/change-password')
                self.assertEqual(response.status_code, 302)

                # try the post without login
                response = c.post('/en_US/change-password', data={
                    'password': data['password'],
                    'confirm': data['password']
                })
                self.assertEqual(response.status_code, 302)

                # Login now
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': data['email'],
                        'password': data['password']
                    })
                self.assertEqual(response.status_code, 302)

                # send wrong password confirm
                response = c.post('/en_US/change-password', data={
                    'password': 'new-password',
                    'confirm': 'password'
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue("Passwords must match" in response.data)

                # send correct password confirm but not old password
                response = c.post('/en_US/change-password', data={
                    'password': 'new-password',
                    'confirm': 'new-password'
                })
                self.assertEqual(response.status_code, 200)

                # send correct password confirm but not old password
                response = c.post('/en_US/change-password', data={
                    'old_password': 'passw',
                    'password': 'new-password',
                    'confirm': 'new-password'
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    "The current password you entered is invalid" in response.data
                )

                response = c.post('/en_US/change-password', data={
                    'old_password': data['password'],
                    'password': 'new-password',
                    'confirm': 'new-password'
                })
                self.assertEqual(response.status_code, 302)
                response = c.get('/en_US')

                # Login now using new password
                response = c.post('/en_US/login',
                    data={
                        'email': data['email'],
                        'password': 'new-password'
                    })
                self.assertEqual(response.status_code, 302)

    def test_0040_reset_account(self):
        """
        Allow resetting password of the user
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            data = {
                'name': 'Registered User',
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company_id,
            }
            registered_user_id = self.nereid_user_obj.create(data.copy())

            with app.test_client() as c:

                # Try reset without login and page should render
                response = c.get('/en_US/reset-account')
                self.assertEqual(response.status_code, 200)

                # Try resetting password through email
                response = c.post('/en_US/reset-account', data={
                    'email': data['email'],
                })
                self.assertEqual(response.status_code, 302)

                regd_user = self.nereid_user_obj.browse(registered_user_id)
                self.assertTrue(regd_user.activation_code)

                # A successful login after requesting activation code should
                # just clear the activation code.
                response = c.post(
                    '/en_US/login',
                    data={
                        'email': data['email'],
                        'password': data['password'],
                    }
                )
                self.assertEqual(response.status_code, 302)
                regd_user = self.nereid_user_obj.browse(registered_user_id)
                self.assertFalse(regd_user.activation_code)

            with app.test_client() as c:
                # Try to reset again - with good intentions
                response = c.post('/en_US/reset-account', data={
                    'email': data['email'],
                })
                self.assertEqual(response.status_code, 302)

                regd_user = self.nereid_user_obj.browse(registered_user_id)
                self.assertTrue(regd_user.activation_code)

                response = c.get(
                    '/en_US/activate-account/%d/%s' % (
                        regd_user.id, regd_user.activation_code
                    )
                )
                self.assertEqual(response.status_code, 302)
                self.assertTrue('/en_US/new-password' in response.data)

                response = c.post('/en_US/new-password', data={
                    'password': 'reset-password',
                    'confirm': 'reset-password'
                })
                self.assertEqual(response.status_code, 302)

                regd_user = self.nereid_user_obj.browse(registered_user_id)
                self.assertFalse(regd_user.activation_code)

                response = c.post('/en_US/login',
                    data={
                        'email': data['email'],
                        'password': 'wrong-password'
                    }
                )
                self.assertEqual(response.status_code, 200)     # Login rejected

                response = c.post('/en_US/login',
                    data={
                        'email': data['email'],
                        'password': 'reset-password'
                    }
                )
                self.assertEqual(response.status_code, 302)     # Login approved

    def test_0050_logout(self):
        """
        Check for logout
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            data = {
                'name': 'Registered User',
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company_id,
            }
            self.nereid_user_obj.create(data.copy())

            with app.test_client() as c:
                response = c.get("/en_US/account")
                self.assertEqual(response.status_code, 302)

                # Login and check again
                response = c.post(
                    '/en_US/login',
                    data={'email': data['email'], 'password': data['password']}
                )
                self.assertEqual(response.status_code, 302)

                response = c.get("/en_US/account")
                self.assertEqual(response.status_code, 200)

                response = c.get("/en_US/logout")
                self.assertEqual(response.status_code, 302)

                response = c.get("/en_US/account")
                self.assertEqual(response.status_code, 302)

    def test_0060_has_perm(self):
        """Test the has_perm decorator
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            @permissions_required(['admin'])
            def test_permission_1():
                return True

            with app.test_request_context():
                self.assertRaises(Forbidden, test_permission_1)

            perm_admin = self.nereid_permission_obj.create({
                'name': 'Admin',
                'value': 'admin',
            })
            perm_nereid_admin = self.nereid_permission_obj.create({
                'name': 'Nereid Admin',
                'value': 'nereid_admin',
            })

            self.nereid_user_obj.write(
                self.guest_user_id, {'permissions': [('set', [perm_admin])]}
            )
            @permissions_required(['admin'])
            def test_permission_2():
                return True

            with app.test_request_context():
                self.assertTrue(test_permission_2())

            @permissions_required(['admin', 'nereid_admin'])
            def test_permission_3():
                return True

            with app.test_request_context():
                self.assertRaises(Forbidden, test_permission_3)

            self.nereid_user_obj.write(
                self.guest_user_id,
                {'permissions': [('set', [perm_admin, perm_nereid_admin])]}
            )
            with app.test_request_context():
                self.assertTrue(test_permission_3())


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAuth)
        )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
