#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

    Test the Internationalisation

    :copyright: (c) 2012-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from nereid.testing import NereidTestCase
from trytond.transaction import Transaction
from trytond.modules.nereid.i18n import _, N_


class TestI18N(NereidTestCase):
    """
    Test the internationalisation
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
        }
        return templates.get(name)

    def test_0010_simple_txn(self):
        """
        Test if the translations work in a simple env
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            s = _("en_US")
            self.assertEqual(s, u'en_US')
            with Transaction().set_context(language="pt_BR"):
                self.assertEqual(s, u'pt_BR')

    def test_0020_kwargs(self):
        """
        Test if kwargs work
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            s = _("Hi %(name)s", name="Sharoon")
            self.assertEqual(s, u"Hi Sharoon")
            with Transaction().set_context(language="pt_BR"):
                self.assertEqual(s, u'Oi Sharoon')

    def test_0030_ngettext(self):
        """
        Test if ngettext work
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.assertEqual(
                N_("%(num)d apple", "%(num)d apples", 1), u"1 apple"
            )
            self.assertEqual(
                N_("%(num)d apple", "%(num)d apples", 2), u"2 apples"
            )


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestI18N)
        )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
