# -*- coding: utf-8 -*-
"""
    test_static_file

    Test the static file feature of nereid  

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import base64
import unittest2 as unittest

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
CONFIG.options['data_path'] = '/tmp/temp_tryton_data/'

from trytond.modules import register_classes
register_classes()
from nereid.testing import testing_proxy, TestCase
from trytond.transaction import Transaction


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


def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestStaticFile)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
