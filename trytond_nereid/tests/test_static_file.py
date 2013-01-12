#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    test_static_file

    Test the static file feature of nereid  

    :copyright: (c) 2012-2013 by Openlabs Technologies & Consulting (P) LTD
    :license: GPLv3, see LICENSE for more details.
"""
import new
import unittest
import functools

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from trytond.config import CONFIG
from nereid.testing import NereidTestCase
from nereid import render_template

CONFIG['smtp_server'] = 'smtpserver'
CONFIG['smtp_user'] = 'test@xyz.com'
CONFIG['smtp_password'] = 'testpassword'
CONFIG['smtp_port'] = 587
CONFIG['smtp_tls'] = True
CONFIG['smtp_from'] = 'from@xyz.com'
CONFIG.options['data_path'] = '/tmp/temp_tryton_data/'


class TestStaticFile(NereidTestCase):

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
        self.static_file_obj = POOL.get('nereid.static.file')
        self.static_folder_obj = POOL.get('nereid.static.folder')

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

        url_map_id, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        self.nereid_website_obj.create({
            'name': 'localhost',
            'url_map': url_map_id,
            'company': company_id,
            'application_user': USER,
            'default_language': en_us,
            'guest_user': guest_user,
        })

    def get_template_source(self, name):
        """
        Return templates
        """
        templates = {
            'localhost/home.jinja':
                '''
                {% set static_file = static_file_obj.browse(static_file_id) %}
                {{ static_file.url }}
                ''',

        }
        return templates.get(name)

    def create_static_file(self, file_buffer):
        """
        Creates the static file for testing
        """
        folder_id = self.static_folder_obj.create({
            'folder_name': 'test',
            'description': 'Test Folder'
        })

        return self.static_file_obj.create({
            'name': 'test.png',
            'folder': folder_id,
            'file_binary': file_buffer,
        })

    def test_0010_static_file(self):
        """
        Create a static folder, and a static file
        And check if it can be fetched
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            file_buffer = buffer('test-content')
            file_id = self.create_static_file(file_buffer)
            static_file = self.static_file_obj.browse(file_id)
            self.assertEqual(static_file.file_binary, file_buffer)

            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/en_US/static-file/test/test.png')
                self.assertEqual(rv.data, 'test-content')
                self.assertEqual(rv.headers['Content-Type'], 'image/png')
                self.assertEqual(rv.status_code, 200)

    def test_0020_static_file_url(self):
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            file_buffer = buffer('test-content')
            file_id = self.create_static_file(file_buffer)
            file = self.static_file_obj.browse(file_id)
            self.assertFalse(file.url)

            app = self.get_app()
            static_file_obj = self.static_file_obj
            with app.test_client() as c:
                # Patch the home page method
                def home_func(self, file_id):
                    return render_template(
                        'home.jinja',
                        static_file_obj=static_file_obj,
                        static_file_id=file_id,
                    )
                home_func = functools.partial(home_func, file_id=file_id)
                c.application.view_functions[
                    'nereid.website.home'] = new.instancemethod(
                        home_func, self.nereid_website_obj
                )
                self.nereid_website_obj.home = new.instancemethod(
                    home_func, self.nereid_website_obj
                )
                rv = c.get('/en_US/')
                self.assertTrue('/en_US/static-file/test/test.png' in rv.data)
                self.assertEqual(rv.status_code, 200)

    def test_0030_static_file_remote_url(self):
        """
        Test a static file with remote type
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            folder_id = self.static_folder_obj.create({
                'folder_name': 'test',
                'description': 'Test Folder'
            })
            file_id = self.static_file_obj.create({
                'name': 'remote.png',
                'folder': folder_id,
                'type': 'remote',
                'remote_path': 'http://openlabs.co.in/logo.png',
            })
            file = self.static_file_obj.browse(file_id)
            self.assertFalse(file.url)

            app = self.get_app()
            static_file_obj = POOL.get('nereid.static.file')
            with app.test_client() as c:
                # Patch the home page method
                def home_func(self, file_id):
                    return render_template(
                        'home.jinja',
                        static_file_obj=static_file_obj,
                        static_file_id=file_id,
                    )
                home_func = functools.partial(home_func, file_id=file_id)
                c.application.view_functions[
                    'nereid.website.home'] = new.instancemethod(
                        home_func, self.nereid_website_obj
                )
                self.nereid_website_obj.home = new.instancemethod(
                    home_func, self.nereid_website_obj
                )
                rv = c.get('/en_US/')
                self.assertTrue(
                    'http://openlabs.co.in/logo.png' in rv.data
                )
                self.assertEqual(rv.status_code, 200)


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestStaticFile)
        )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
