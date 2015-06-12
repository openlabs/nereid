#!/usr/bin/env python
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import urllib
import unittest
import base64
import json

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
        self.nereid_website_locale_obj = POOL.get('nereid.website.locale')
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

        url_map, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        currency, = self.currency_obj.search([('code', '=', 'USD')])
        locale, = self.nereid_website_locale_obj.create([{
            'code': 'en_US',
            'language': en_us,
            'currency': currency,
        }])
        self.nereid_website_obj.create([{
            'name': 'localhost',
            'url_map': url_map,
            'company': self.company,
            'application_user': USER,
            'default_locale': locale,
            'guest_user': self.guest_user,
        }])
        self.templates = {
            'home.jinja': '{{get_flashed_messages()}}',
            'login.jinja':
            '{{ login_form.errors }} {{get_flashed_messages()}}',
            'registration.jinja':
            '{{ form.errors }} {{get_flashed_messages()}}',
            'reset-password.jinja': '{{get_flashed_messages()}}',
            'change-password.jinja':
            '''{{ change_password_form.errors }}
            {{get_flashed_messages()}}''',
            'address-edit.jinja': 'Address Edit {{ form.errors }}',
            'address.jinja': '',
            'account.jinja': '',
            'profile.jinja': '{{ request.nereid_user.display_name }}',
            'emails/activation-text.jinja': 'activation-email-text',
            'emails/activation-html.jinja': 'activation-email-html',
            'emails/reset-text.jinja': 'reset-email-text',
            'emails/reset-html.jinja': 'reset-email-html',
        }

    def get_template_source(self, name):
        """
        Return templates
        """

        return self.templates.get(name)

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
                response = c.get('/registration')
                self.assertEqual(response.status_code, 200)   # GET Request

                data = {
                    'name': 'Registered User',
                    'email': 'regd_user@openlabs.co.in',
                    'password': 'password'
                }
                # Post with missing password
                response = c.post('/registration', data=data)
                self.assertEqual(response.status_code, 200)  # Form rejected

                data['confirm'] = 'password'
                response = c.post('/registration', data=data)
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

            with Transaction().set_context(active_test=False):
                self.assertEqual(
                    self.nereid_user_obj.search(
                        [('email', '=', data['email'])], count=True
                    ), 1
                )

            # Try to register the same user again
            response = c.post('/registration', data=data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                "A registration already exists with this email" in response.data
            )

    def test_0015_register_json(self):
        """
        Registration must create a new party.

        Same as registration test but with json data
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                response = c.get('/registration')
                self.assertEqual(response.status_code, 200)   # GET Request

                data = {
                    'name': 'Registered User',
                    'email': 'regd_user@openlabs.co.in',
                    'password': 'password'
                }
                # Post with missing password
                response = c.post(
                    '/registration', data=json.dumps(data),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)  # Form rejected

                data['confirm'] = 'password'
                response = c.post(
                    '/registration',
                    data=json.dumps(data),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 201)

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

            with Transaction().set_context(active_test=False):
                self.assertEqual(
                    self.nereid_user_obj.search(
                        [('email', '=', data['email'])], count=True
                    ), 1
                )

            # Try to register the same user again
            response = c.post(
                '/registration',
                data=json.dumps(data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 400)
            self.assertTrue(
                "A registration already exists with this email" in response.data
            )

    def test_0015_match_password(self):
        """
        Assert that matching of password works
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            usd, = self.currency_obj.create([{
                'name': 'US Dollar',
                'code': 'USD',
                'symbol': '$',
            }])
            party, = self.party_obj.create([{
                'name': 'Openlabs',
            }])
            company, = self.company_obj.create([{
                'party': party,
                'currency': usd,
            }])
            registered_user_party = self.party_obj(name='Registered User')
            registered_user_party.save()
            registered_user, = self.nereid_user_obj.create([{
                'party': registered_user_party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': company,
            }])
            self.assertTrue(registered_user.match_password('password'))

    def test_0015_verify_email(self):
        """
        Check that the verification of email is working
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
                response = c.post('/registration', data=data)
                self.assertEqual(response.status_code, 302)

                with Transaction().set_context(active_test=False):
                    registered_user, = self.nereid_user_obj.search(
                        [('email', '=', data['email'])]
                    )
                self.assertFalse(registered_user.email_verified)

                # Verify the email with invaild code
                invalid_code = "thisisinvalidcode"
                response = c.get(
                    '/verify-email/%s/%s' %
                    (registered_user.id, invalid_code)
                )
                self.assertEqual(response.status_code, 302)
                self.assertFalse(registered_user.email_verified)

                # verify the email
                response = c.get(registered_user.get_email_verification_link())
                self.assertEqual(response.status_code, 302)

                # Email should now be verified
                self.assertTrue(registered_user.email_verified)

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
                response = c.post('/registration', data=data)
                self.assertEqual(response.status_code, 302)

                with Transaction().set_context(active_test=False):
                    registered_user, = self.nereid_user_obj.search(
                        [('email', '=', data['email'])]
                    )
                self.assertFalse(registered_user.active)

                # Login should fail since there is activation code
                response = c.post(
                    '/login',
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
                response = c.get(registered_user.get_activation_link())
                self.assertEqual(response.status_code, 302)
                registered_user = self.nereid_user_obj(registered_user.id)

                # The account must be active
                self.assertTrue(registered_user.active)
                # Email should be verified
                self.assertTrue(registered_user.email_verified)

                # Login should work
                response = c.post(
                    '/login',
                    data={
                        'email': data['email'],
                        'password': data['password'],
                    }
                )
                registered_user = self.nereid_user_obj(registered_user.id)
                self.assertEqual(response.status_code, 302)

    def test_0030_change_password(self):
        """
        Check password changing functionality
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                # try the page without login
                response = c.get('/change-password')
                self.assertEqual(response.status_code, 302)

                # try the post without login
                response = c.post('/change-password', data={
                    'password': data['password'],
                    'confirm': data['password']
                })
                self.assertEqual(response.status_code, 302)

                # Login now
                response = c.post(
                    '/login',
                    data={
                        'email': data['email'],
                        'password': data['password']
                    })
                self.assertEqual(response.status_code, 302)

                # send wrong password confirm
                response = c.post('/change-password', data={
                    'password': 'new-password',
                    'confirm': 'password'
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue("Passwords must match" in response.data)

                # send correct password confirm but not old password
                response = c.post('/change-password', data={
                    'password': 'new-password',
                    'confirm': 'new-password'
                })
                self.assertEqual(response.status_code, 200)

                # send correct password confirm but not old password
                response = c.post('/change-password', data={
                    'old_password': 'passw',
                    'password': 'new-password',
                    'confirm': 'new-password'
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    "The current password you entered is invalid"
                    in response.data
                )

                response = c.post('/change-password', data={
                    'old_password': data['password'],
                    'password': 'new-password',
                    'confirm': 'new-password'
                })
                self.assertEqual(response.status_code, 302)
                response = c.get('/')

                # Login now using new password
                response = c.post(
                    '/login',
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

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            regd_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:

                # Try reset without login and page should render
                response = c.get('/reset-account')
                self.assertEqual(response.status_code, 200)

                # Try resetting password through email
                response = c.post('/reset-account', data={
                    'email': data['email'],
                })
                self.assertEqual(response.status_code, 302)

                response = c.post(
                    '/reset-account',
                    data={
                        'email': data['email'],
                    },
                    headers={'X-Requested-With': 'XMLHTTPRequest'}
                )
                self.assertEqual(response.status_code, 200)

                rv = c.post(
                    '/reset-account',
                    data={
                        'email': 'made_up_email@test.com',
                    },
                    headers={'X-Requested-With': 'XMLHTTPRequest'}
                )
                self.assertEqual(rv.status_code, 400)
                self.assertEqual(
                    json.loads(rv.data), {'message': 'Invalid email address'}
                )

                # A successful login after requesting activation code should
                # not do anything but just allow login
                response = c.post(
                    '/login',
                    data={
                        'email': data['email'],
                        'password': data['password'],
                    }
                )
                self.assertEqual(response.status_code, 302)

            with app.test_client() as c:
                # Try to reset again - with good intentions
                response = c.post('/reset-account', data={
                    'email': data['email'],
                })
                self.assertEqual(response.status_code, 302)

                # Try to reset password with invalid code
                invalid_code = 'thisistheinvalidcode'
                response = c.post(
                    '/new-password/%s/%s' % (regd_user.id, invalid_code),
                    data={
                        'password': 'reset-password',
                        'confirm': 'reset-password'
                    }
                )
                self.assertEqual(response.status_code, 302)

                response = c.post(
                    '/login',
                    data={
                        'email': data['email'],
                        'password': 'reset-password'
                    }
                )
                self.assertEqual(response.status_code, 200)  # Login rejected

                # Reset password with valid code
                response = c.post(regd_user.get_reset_password_link(), data={
                    'password': 'reset-password',
                    'confirm': 'reset-password'
                })
                self.assertEqual(response.status_code, 302)

                regd_user = self.nereid_user_obj(regd_user.id)

                response = c.post(
                    '/login',
                    data={
                        'email': data['email'],
                        'password': 'wrong-password'
                    }
                )
                self.assertEqual(response.status_code, 200)     # Login rejected

                response = c.post(
                    '/login',
                    data={
                        'email': data['email'],
                        'password': 'reset-password'
                    }
                )
                self.assertEqual(response.status_code, 302)     # Login approved

            with app.test_client() as c:
                # Try to reset again - with bad intentions

                # Bad request because there is no email
                response = c.post(
                    '/reset-account', data={},
                    headers={'X-Requested-With': 'XMLHTTPRequest'}
                )
                self.assertEqual(response.status_code, 400)

                response = c.post('/reset-account', data={})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    'Invalid email address' in response.data
                )

                # Bad request because there is empty email
                response = c.post('/reset-account', data={'email': ''})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    'Invalid email address' in response.data
                )

            data = {
                'party': party,
                'display_name': 'User without email',
                'email': '',
                'password': 'password',
                'company': self.company,
            }
            email_less_user, = self.nereid_user_obj.create([data.copy()])
            with app.test_client() as c:
                # Bad request because there is empty email
                # this is a special case where there is an user
                # with empty email
                response = c.post('/reset-account', data={'email': ''})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    'Invalid email address' in response.data
                )

    def test_0050_logout(self):
        """
        Check for logout
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                response = c.get("/account")
                self.assertEqual(response.status_code, 302)

                # Login and check again
                response = c.post(
                    '/login',
                    data={'email': data['email'], 'password': data['password']}
                )
                self.assertEqual(response.status_code, 302)

                response = c.get("/account")
                self.assertEqual(response.status_code, 200)

                response = c.get("/logout")
                self.assertEqual(response.status_code, 302)

                response = c.get("/account")
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

            perm_admin, = self.nereid_permission_obj.create([{
                'name': 'Admin',
                'value': 'admin',
            }])
            perm_nereid_admin, = self.nereid_permission_obj.create([{
                'name': 'Nereid Admin',
                'value': 'nereid_admin',
            }])

    def test_0070_gravatar(self):
        """
        Check if the gravatar is returned by the profile picture
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            self.templates['home.jinja'] = """
            {{ request.nereid_user.get_profile_picture() }}
            """

            with app.test_client() as c:
                response = c.get('/')
                self.assertTrue(
                    'http://www.gravatar.com/avatar/' in response.data
                )

    def test_0090_profile(self):
        """
        Test the profile functionality
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                response = c.get('/me')
                self.assertEqual(response.status_code, 302)

                # Login and check again
                response = c.post(
                    '/login',
                    data={'email': data['email'], 'password': data['password']}
                )
                response = c.get('/me')
                self.assertEqual(response.data, data['display_name'])

                # Change the display name of the user
                response = c.post(
                    '/me', data={
                        'display_name': 'Regd User',
                        'timezone': 'UTC',
                        'email': 'cannot@openlabs.co.in',
                    }
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, 'Regd User')

    def test_0100_has_permission(self):
        '''
        Test the functionality of has_permissions
        '''
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            p1, p2, p3, p4 = self.nereid_permission_obj.create([
                {'name': 'p1', 'value': 'nereid.perm1'},
                {'name': 'p2', 'value': 'nereid.perm2'},
                {'name': 'p3', 'value': 'nereid.perm3'},
                {'name': 'p4', 'value': 'nereid.perm4'},
            ])
            self.nereid_user_obj.write(
                [self.guest_user],
                {
                    'permissions': [
                        ('add', [p1, p2])
                    ]
                }
            )

            # all = [], any = [] = True
            self.assertTrue(self.guest_user.has_permissions())

            # all = [p1, p2], any = [] == True
            self.assertTrue(self.guest_user.has_permissions(
                perm_all=[p1.value, p2.value]
            ))

            # all = [p1, p2], any = [p3, p4] == False
            self.assertFalse(self.guest_user.has_permissions(
                perm_all=[p1.value, p2.value],
                perm_any=[p3.value, p4.value]
            ))

            # all = [p1, p3], any = [] == False
            self.assertFalse(self.guest_user.has_permissions(
                perm_all=[p1.value, p3.value],
            ))

            # all = [p1, p3], any = [p1, p3, p4] == False
            self.assertFalse(self.guest_user.has_permissions(
                perm_all=[p1.value, p3.value],
                perm_any=[p1.value, p3.value, p4.value]
            ))

            # all = [p1, p2], any = [p1, p3, p4] == True
            self.assertTrue(self.guest_user.has_permissions(
                perm_all=[p1.value, p2.value],
                perm_any=[p1.value, p3.value, p4.value]
            ))

            # all = [], any = [p1, p2, p3] == True
            self.assertTrue(self.guest_user.has_permissions(
                perm_any=[p1.value, p2.value, p3.value]
            ))

            # all = [], any = [p3, p4] == False
            self.assertFalse(self.guest_user.has_permissions(
                perm_any=[p3.value, p4.value]
            ))

    def test_0110_user_management(self):
        """
        ensure that the cookie gets cleared if the user in session
        is invalid.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                # Login and check again
                response = c.post(
                    '/login',
                    data={'email': data['email'], 'password': data['password']}
                )
                response = c.get('/me')
                self.assertEqual(response.data, data['display_name'])

                # Delete the user
                self.nereid_user_obj.delete([nereid_user])

                response = c.get('/me')
                self.assertEqual(response.status_code, 302)

    def test_200_basic_authentication(self):
        """
        Test if basic authentication works
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                # Login without any auth
                response = c.get('/me')
                self.assertEqual(response.status_code, 302)

                # Login with wrong basic auth
                basic_auth = base64.b64encode(b'email@example.com:oops')
                response = c.get('/me', headers={
                    'Authorization': 'Basic ' +
                    basic_auth.decode('utf-8').strip('\r\n')
                })
                self.assertEqual(response.status_code, 302)

                # Send the same request with correct basic authentication
                basic_auth = base64.b64encode(b'email@example.com:password')
                response = c.get(
                    '/me', headers={
                        'Authorization': 'Basic ' + basic_auth.decode(
                            'utf-8').strip('\r\n')
                    }
                )
                self.assertEqual(response.data, data['display_name'])

    def test_205_basic_authentication_with_separator(self):
        """
        Test if basic authentication works with a separator in the password
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'pass:word',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                # Login without any auth
                response = c.get('/me')
                self.assertEqual(response.status_code, 302)

                # Send the same request with correct basic authentication
                basic_auth = base64.b64encode(b'email@example.com:pass:word')
                response = c.get(
                    '/me', headers={
                        'Authorization': 'Basic ' + basic_auth.decode(
                            'utf-8').strip('\r\n')
                    }
                )
                self.assertEqual(response.data, data['display_name'])

    def test_207_login_basic_authentication_and_active_field(self):
        """
        Check if the active field stop the user from logging in.
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'pass:word',
                'company': self.company,
                'active': False,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                # Send the same request with correct basic authentication
                basic_auth = base64.b64encode(b'email@example.com:pass:word')
                headers = {
                    'Authorization': 'Basic ' + basic_auth.decode(
                        'utf-8').strip('\r\n')
                }

                # By default user accounts are active. So login should
                # work.
                response = c.get('/me', headers=headers)
                self.assertEqual(response.status_code, 302)

            nereid_user.active = True
            nereid_user.save()

            with app.test_client() as c:
                # Send the same request with correct basic authentication
                basic_auth = base64.b64encode(b'email@example.com:pass:word')
                headers = {
                    'Authorization': 'Basic ' + basic_auth.decode(
                        'utf-8').strip('\r\n')
                }

                # By default user accounts are active. So login should
                # work.
                response = c.get('/me', headers=headers)
                self.assertEqual(response.status_code, 200)

    def test_210_token_authentication(self):
        """
        Test if token authentication works
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                # Login without any auth
                response = c.get('/me')
                self.assertEqual(response.status_code, 302)

                # Login with wrong token auth
                token = "something i thought would just work ;-)"
                response = c.get('/me', headers={
                    'Authorization': 'token ' + token
                })
                self.assertEqual(response.status_code, 302)

                # Send the same request with correct token authentication
                response = c.get(
                    '/me', headers={
                        'Authorization': 'token ' + nereid_user.get_auth_token()
                    }
                )
                self.assertEqual(response.data, data['display_name'])

                # Send the same request with correct token authentication
                # but using capital 'T' in 'Token'
                token = nereid_user.get_auth_token()
                response = c.get(
                    '/me', headers={
                        'Authorization': 'Token ' + token
                    }
                )
                self.assertEqual(response.data, data['display_name'])

    def test_0300_test_is_guest_user(self):
        """
        Ensure that is_guest_user works
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            self.templates['home.jinja'] = '{{ request.is_guest_user }}'

            with app.test_client() as c:
                self.assertEqual(c.get('/').data, 'True')
                c.post(
                    '/login',
                    data={'email': data['email'], 'password': data['password']}
                )
                self.assertEqual(c.get('/').data, 'False')

    def test_0400_auth_xhr_wrong(self):
        """
        Ensure that auth in XHR sends the right results
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                self.assertEqual(c.get('/me').status_code, 302)

                rv = c.post(
                    '/login',
                    data={'email': data['email'], 'password': 'wrong'},
                    headers={'X-Requested-With': 'XMLHTTPRequest'}
                )
                self.assertEqual(rv.status_code, 401)
                self.assertEqual(
                    json.loads(rv.data), {'message': 'Bad credentials'}
                )
                self.assertEqual(c.get('/me').status_code, 302)

    def test_0410_auth_xhr_valid(self):
        """
        Ensure that auth in XHR sends the right results
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                self.assertEqual(c.get('/me').status_code, 302)

                rv = c.post(
                    '/login',
                    data={'email': data['email'], 'password': data['password']},
                    headers={'X-Requested-With': 'XMLHTTPRequest'}
                )
                self.assertEqual(rv.status_code, 200)
                data = json.loads(rv.data)

                self.assertTrue(data['success'])
                self.assertTrue('user' in data)

                self.assertEqual(c.get('/me').status_code, 200)

    def test_0420_auth_token_basic(self):
        """
        Try to get authentication token with basic auth
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                self.assertEqual(c.get('/me').status_code, 302)

                # wrong credentials first
                basic_auth = base64.b64encode(b'email@example.com:oops')
                rv = c.post('/login/token', headers={
                    'Authorization': 'Basic ' +
                        basic_auth.decode('utf-8').strip('\r\n'),
                    'X-Requested-With': 'XMLHTTPRequest',
                })
                self.assertEqual(rv.status_code, 401)
                self.assertEqual(
                    json.loads(rv.data), {'message': 'Bad credentials'}
                )

                # Send right credentials
                basic_auth = base64.b64encode(b'email@example.com:password')
                rv = c.post('/login/token', headers={
                    'Authorization': 'Basic ' +
                        basic_auth.decode('utf-8').strip('\r\n'),
                    'X-Requested-With': 'XMLHTTPRequest',
                })
                self.assertEqual(rv.status_code, 200)
                data = json.loads(rv.data)

                self.assertTrue('user' in data)
                self.assertTrue('token' in data)

    def test_0430_remember_me(self):
        """
        Ensure that remember me in login is working
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            party, = self.party_obj.create([{'name': 'Registered user'}])
            data = {
                'party': party,
                'display_name': 'Registered User',
                'email': 'email@example.com',
                'password': 'password',
                'company': self.company,
            }
            nereid_user, = self.nereid_user_obj.create([data.copy()])

            with app.test_client() as c:
                response = c.post(
                    '/login',
                    data={
                        'email': data['email'], 'password': data['password'],
                        'remember': ''
                    }
                )
                self.assertEqual(response.status_code, 302)

                response = c.get('/me')
                self.assertEqual(response.status_code, 200)

                with c.session_transaction() as sess:
                    sess.clear()

                response = c.get("/me")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                        urllib.unquote(response.location),
                        'http://localhost/login?next=/me'
                )

                response = c.post(
                    '/login',
                    data={
                        'email': data['email'], 'password': data['password'],
                        'remember': 'True'
                    }
                )
                self.assertEqual(response.status_code, 302)

                response = c.get("/me")
                self.assertEqual(response.status_code, 200)

                with c.session_transaction() as sess:
                    sess.clear()

                response = c.get("/me")
                self.assertEqual(response.status_code, 200)


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAuth)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
