#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from ast import literal_eval
import unittest2 as unittest

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
from trytond.modules import register_classes
register_classes()

from nereid.testing import testing_proxy
from trytond.transaction import Transaction


class TestLanguage(unittest.TestCase):
    """Test Language"""

    @classmethod
    def setUpClass(cls):
        testing_proxy.install_module('nereid')
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            company = testing_proxy.create_company('Test Company')
            cls.guest_user = testing_proxy.create_guest_user()
            cls.site = testing_proxy.create_site('testsite.com')
            testing_proxy.create_template(
                'home.jinja',
                "{{request.nereid_language.code}}",
                cls.site)
            txn.cursor.commit()

    def get_app(self):
        return testing_proxy.make_app(
            SITE='testsite.com', 
            GUEST_USER=self.guest_user,
            SESSION_STORE_CLASS = 'nereid.session.FilesystemSessionStore',
            )

    def setUp(self):
        self.lang_obj = testing_proxy.pool.get('ir.lang')
        self.site_obj = testing_proxy.pool.get('nereid.website')
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            lang_ids = self.lang_obj.search([])
            self.langs = self.lang_obj.read(lang_ids, ['code'])

    def test_0010_set_currency(self):
        """Test if the language change is retained
        """
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/')
            self.assertEqual(rv.data, 'en_US')

        with app.test_client() as c:
            c.get('/en_US/set_language?language=%s&next=/' % self.langs[0]['code'])
            rv = c.get('/en_US/')
            self.assertEqual(rv.data, self.langs[0]['code'])

    def test_0020_set_another(self):
        """Test if the language change is retained
        """
        app = self.get_app()
        with app.test_client() as c:
            c.get('/en_US/set_language?language=%s&next=/' % self.langs[1]['code'])
            rv = c.get('/en_US/')
            self.assertEqual(rv.data, self.langs[1]['code'])

    def test_0030_set_with_lang_template(self):
        """Test and ensure the language paramenter on template is respected
        """
        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            testing_proxy.create_template(
                'home.jinja',
                "%s:{{request.nereid_language.code}}" % self.langs[1]['code'],
                self.site, self.langs[1]['code'])
            txn.cursor.commit()

        app = self.get_app()
        with app.test_client() as c:
            c.get('/en_US/set_language?language=%s&next=/' % self.langs[1]['code'])
            rv = c.get('/en_US/')
            self.assertEqual(rv.data, '%s:%s' % (
                self.langs[1]['code'], self.langs[1]['code']
                )
            )


def suite():
    "Language test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestLanguage)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
