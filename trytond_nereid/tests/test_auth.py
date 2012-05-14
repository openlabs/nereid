# -*- coding: utf-8 -*-
"""

    Test the Auth layer

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
from trytond.pool import Pool

NEW_USER = 'new@example.com'
NEW_PASS = 'password'


class TestAuth(TestCase):
    """
    Test Auth Layer
    """

    @classmethod
    def setUpClass(cls):
        super(TestAuth, cls).setUpClass()
        # Install module
        testing_proxy.install_module('nereid')

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            country_obj = Pool().get('country.country')
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
                'home.jinja', '{{ get_flashed_messages() }}', cls.site
            )
            testing_proxy.create_template(
                'login.jinja',
                '{{ login_form.errors }} {{ get_flashed_messages() }}',
                cls.site
            )
            testing_proxy.create_template(
                'registration.jinja',
                '{{ form.errors }} {{get_flashed_messages()}}',
                cls.site
            )

            testing_proxy.create_template('reset-password.jinja',
                '{{get_flashed_messages()}}', cls.site
            )
            testing_proxy.create_template(
                'change-password.jinja',
                '''{{ change_password_form.errors }}
                {{ get_flashed_messages() }}''',
                cls.site
            )
            testing_proxy.create_template(
                'address-edit.jinja',
                '{{ form.errors }}',
                cls.site
            )
            testing_proxy.create_template('address.jinja', '', cls.site)
            testing_proxy.create_template('account.jinja', '', cls.site)

            txn.cursor.commit()

    def get_app(self, **options):
        options.update({
            'SITE': 'testsite.com',
            'GUEST_USER': self.guest_user,
        })
        return testing_proxy.make_app(**options)

    def setUp(self):
        self.nereid_user_obj = testing_proxy.pool.get('nereid.user')

    def test_0010_register(self):
        """
        Registration must create a new party
        """
        app = self.get_app()

        # Test if the registration form gets rendered without issues
        with app.test_client() as c:
            response = c.get('/en_US/registration')
            self.assertEqual(response.status_code, 200)

        with app.test_client() as c:
            data = {
                'name': 'New Test Registered User',
                'email': 'new.test@example.com',
                'password': 'password'
            }
            response = c.post('/en_US/registration', data=data)
            self.assertEqual(response.status_code, 200)

            data['confirm'] = 'password'
            response = c.post('/en_US/registration', data=data)
            self.assertEqual(response.status_code, 302)

        with app.test_client() as c:
            data = {
                'name': 'New Test Registered User',
                'email': 'new.test@example.com',
                'password': 'password',
                'confirm': 'password',
            }
            response = c.post('/en_US/registration', data=data)
            self.assertEqual(response.status_code, 200)


    def test_0020_activation(self):
        """
        Check if activation workflow is fine
        """
        app = self.get_app()

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            new_user_id, = self.nereid_user_obj.search(
                [('email', '=', 'new.test@example.com')]
            )
            new_user = self.nereid_user_obj.browse(new_user_id)
            self.assertTrue(new_user.activation_code != False)

            txn.cursor.commit()

        with app.test_client() as c:
            response = c.post('/en_US/login',
                data={
                    'email': u'new.test@example.com',
                    'password': u'password'
                })
            self.assertEqual(response.status_code, 200)
            self.assertTrue(
                "Your account has not been activated yet" in response.data
            )

            response = c.get('/en_US/activate-account/%s/%s' % (
                new_user_id, new_user.activation_code
                )
            )
            self.assertEqual(response.status_code, 302)

            # try login again
            response = c.post('/en_US/login',
                data={
                    'email': u'new.test@example.com',
                    'password': u'password'
                })
            self.assertEqual(response.status_code, 302)

    def test_0030_change_password(self):
        """
        Check if changing own password is possible
        """
        app = self.get_app()
        with app.test_client() as c:
            # try the page without login
            response = c.get('/en_US/change-password')
            self.assertEqual(response.status_code, 302)

            # try the post without login
            response = c.post('/en_US/change-password', data={
                'password': 'new-password',
                'confirm': 'password'
            })
            self.assertEqual(response.status_code, 302)

            # Login now
            response = c.post('/en_US/login',
                data={
                    'email': u'new.test@example.com',
                    'password': u'password'
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
                'old_password': 'password',
                'password': 'new-password',
                'confirm': 'new-password'
            })
            self.assertEqual(response.status_code, 302)
            response = c.get('/en_US')

    def test_0040_reset_account(self):
        """
        Allow resetting password of the user
        """
        with Transaction().start(
                    testing_proxy.db_name, testing_proxy.user, None):
            new_user_id, = self.nereid_user_obj.search(
                    [('email', '=', 'new.test@example.com')]
            )

        app = self.get_app()
        with app.test_client() as c:

            # Try reset without login
            response = c.get('/en_US/reset-account')
            self.assertEqual(response.status_code, 200)
            response = c.post('/en_US/reset-account', data={
                'email': 'new.test@example.com',
            })
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            new_user = self.nereid_user_obj.browse(new_user_id)
            self.assertTrue(new_user.activation_code)

        with app.test_client() as c:
            # Try a Login now and the existing activation code for reset should
            # not be there
            response = c.post(
                '/en_US/login',
                data={
                    'email': 'new.test@example.com',
                    'password': 'new-password'
                }
            )
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            new_user = self.nereid_user_obj.browse(new_user_id)
            self.assertFalse(new_user.activation_code)

        with app.test_client() as c:
            # Try to reset again
            response = c.get('/en_US/reset-account')
            self.assertEqual(response.status_code, 200)
            response = c.post('/en_US/reset-account', data={
                'email': 'new.test@example.com',
            })
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            new_user = self.nereid_user_obj.browse(new_user_id)
            self.assertTrue(new_user.activation_code != False)
            activation_code = new_user.activation_code

        with app.test_client() as c:
            response = c.get(
                '/en_US/activate-account/%d/%s' % (new_user_id, activation_code)
            )
            self.assertEqual(response.status_code, 302)

            response = c.post('/en_US/new-password', data={
                'password': 'password',
                'confirm': 'password'
            })
            self.assertEqual(response.status_code, 302)

        with Transaction().start(
                testing_proxy.db_name, testing_proxy.user, None):
            new_user = self.nereid_user_obj.browse(new_user_id)
            self.assertFalse(new_user.activation_code)

        with app.test_client() as c:
            response = c.post('/en_US/login',
                data={
                    'email': 'new.test@example.com', 'password': 'new-password'
                }
            )
            self.assertEqual(response.status_code, 200)     # Login rejected
            response = c.post('/en_US/login',
                data={'email': 'new.test@example.com', 'password': 'password'})
            self.assertEqual(response.status_code, 302)     # Login approved

    def test_0080_login(self):
        """
        Check for login with the next argument
        """
        app = self.get_app()
        with app.test_client() as c:
            response = c.post('/en_US/login?next=/en_US',
                data={'email': 'new.test@example.com', 'password': 'password'})
            self.assertEqual(response.status_code, 302)     # Login approved 
            self.assertTrue('<a href="/en_US">' in response.data)

    def test_0090_logout(self):
        """
        Check for logout and consistent behavior
        """
        app = self.get_app()
        with app.test_client() as c:
            response = c.get("/en_US/account")
            self.assertEqual(response.status_code, 302)

            # Login and check again
            response = c.post('/en_US/login',
                data={'email': 'new.test@example.com', 'password': 'password'})
            self.assertEqual(response.status_code, 302)

            response = c.get("/en_US/account")
            self.assertEqual(response.status_code, 200)

            response = c.get("/en_US/logout")
            self.assertEqual(response.status_code, 302)

            response = c.get("/en_US/account")
            self.assertEqual(response.status_code, 302)

    def test_0100_my_account(self):
        """
        Check if my account page can only be accessed while logged in
        """
        app = self.get_app()
        with app.test_client() as c:
            response = c.get("/en_US/account")
            self.assertEqual(response.status_code, 302)

            # Login and check again
            response = c.post('/en_US/login',
                data={'email': 'new.test@example.com', 'password': 'password'})
            self.assertEqual(response.status_code, 302)

            response = c.get("/en_US/account")
            self.assertEqual(response.status_code, 200)


def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAuth)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
