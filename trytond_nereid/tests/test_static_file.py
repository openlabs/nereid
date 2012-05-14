# -*- coding: utf-8 -*-
"""
    test_static_file

    Test the static file feature of nereid  

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import new
import base64
import functools
import unittest2 as unittest

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
CONFIG.options['data_path'] = '/tmp/temp_tryton_data/'

from trytond.modules import register_classes
register_classes()
from nereid import render_template
from nereid.testing import testing_proxy, TestCase
from trytond.transaction import Transaction
from trytond.pool import Pool


class TestStaticFile(TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestStaticFile, cls).setUpClass()

        testing_proxy.install_module('nereid')  # Install module

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            company = testing_proxy.create_company('Test Company')
            testing_proxy.set_company_for_user(1, company)

            cls.guest_user = testing_proxy.create_guest_user(company=company)

            cls.site = testing_proxy.create_site(
                'localhost',
                application_user = 1, guest_user = cls.guest_user
            )

            # Create a homepage template
            testing_proxy.create_template(
                'home.jinja',
                '''
                {% set static_file = static_file_obj.browse(static_file_id) %}
                {{ static_file.url }}
                ''', cls.site
            )

            txn.cursor.commit()

    def get_app(self, **options):
        options.update({
            'SITE': 'testsite.com',
            'GUEST_USER': self.guest_user,
        })
        return testing_proxy.make_app(**options)

    def setUp(self):
        self.static_folder_obj = testing_proxy.pool.get('nereid.static.folder')
        self.static_file_obj = testing_proxy.pool.get('nereid.static.file')
        self.website_obj = testing_proxy.pool.get('nereid.website')

    def test_000_view(self):
        from trytond.tests.test_tryton import test_view
        test_view('nereid')

    def test_0010_static_file(self):
        """
        Create a static folder, and a static file
        And check if it can be fetched
        """
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            folder_id = self.static_folder_obj.create({
                'folder_name': 'test',
                'description': 'Test Folder'
            })
            encoded_data = base64.encodestring('test-content')
            file_id = self.static_file_obj.create({
                'name': 'test.png',
                'folder': folder_id,
                'file_binary': encoded_data
            })
            static_file = self.static_file_obj.browse(file_id)
            self.assertEqual(static_file.file_binary, encoded_data)

            txn.cursor.commit()

        app = self.get_app()

        with app.test_client() as c:
            rv = c.get('/en_US/static-file/test/test.png')
            self.assertEqual(rv.data, 'test-content')
            self.assertEqual(rv.headers['Content-Type'], 'image/png')
            self.assertEqual(rv.status_code, 200)

    def test_0020_static_file_url(self):
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            file_id, = self.static_file_obj.search([], limit=1)
            file = self.static_file_obj.browse(file_id)
            self.assertFalse(file.url)

        app = self.get_app()
        with app.test_client() as c:
            # Patch the home page method
            def home_func(self, file_id):
                static_file_obj = Pool().get('nereid.static.file')
                return render_template(
                    'home.jinja', 
                    static_file_obj=static_file_obj,
                    static_file_id=file_id,
                )
            home_func = functools.partial(home_func, file_id=file_id)
            c.application.view_functions[
                'nereid.website.home'] = new.instancemethod(
                    home_func, self.website_obj
            )
            self.website_obj.home = new.instancemethod(
                home_func, self.website_obj
            )
            rv = c.get('/en_US/')
            self.assertTrue('/en_US/static-file/test/test.png' in rv.data)
            self.assertEqual(rv.status_code, 200)

    def test_0030_static_file_remote_url(self):
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            folder_id, = self.static_folder_obj.search([])
            file_id = self.static_file_obj.create({
                'name': 'remote.png',
                'folder': folder_id,
                'type': 'remote',
                'remote_path': 'http://openlabs.co.in/logo.png',
            })
            file = self.static_file_obj.browse(file_id)
            self.assertFalse(file.url)
            txn.cursor.commit()

        app = self.get_app()
        with app.test_client() as c:
            # Patch the home page method
            def home_func(self, file_id):
                static_file_obj = Pool().get('nereid.static.file')
                return render_template(
                    'home.jinja',
                    static_file_obj=static_file_obj,
                    static_file_id=file_id,
                )
            home_func = functools.partial(home_func, file_id=file_id)
            c.application.view_functions[
                'nereid.website.home'] = new.instancemethod(
                    home_func, self.website_obj
            )
            self.website_obj.home = new.instancemethod(
                home_func, self.website_obj
            )
            rv = c.get('/en_US/')
            self.assertTrue(
                'http://openlabs.co.in/logo.png' in rv.data
            )
            self.assertEqual(rv.status_code, 200)


def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestStaticFile)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
