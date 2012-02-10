# -*- coding: utf-8 -*-
"""

    Test the Internationalisation

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import unittest2 as unittest

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
from trytond.modules import register_classes
register_classes()
from trytond.modules.nereid.i18n import _, get_translations
from nereid.testing import testing_proxy, TestCase
from trytond.transaction import Transaction


class TestI18N(TestCase):
    """
    Test the internationalisation
    """

    @classmethod
    def setUpClass(cls):
        super(TestI18N, cls).setUpClass()
        testing_proxy.install_module('nereid')

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            company = testing_proxy.create_company('Test Company')
            testing_proxy.set_company_for_user(1, company)

            cls.guest_user = testing_proxy.create_guest_user(company=company)

            txn.cursor.commit()

    def get_app(self, **options):
        options.update({
            'SITE': 'testsite.com',
            'GUEST_USER': self.guest_user,
        })
        return testing_proxy.make_app(**options)

    def test_0010_simple_txn(self):
        """
        Test if the translations work in a simple env
        """
        with Transaction().start(testing_proxy.db_name, 1, None):
            s = _("en_US")
            self.assertEqual(s, u'en_US')
            print get_translations()
            with Transaction().set_context(language="pt_BR"):
                print get_translations(), s, str(s)
                self.assertEqual(s, u'pt_BR')


def suite():
    "Nereid test suite"
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestI18N)
        )
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
