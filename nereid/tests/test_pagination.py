# -*- coding: utf-8 -*-
# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

import trytond.tests.test_tryton
from trytond.transaction import Transaction
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from nereid.contrib.pagination import Pagination, BasePagination


class TestPagination(unittest.TestCase):

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid')

        self.nereid_user_obj = POOL.get('nereid.user')
        self.company_obj = POOL.get('company.company')
        self.party_obj = POOL.get('party.party')
        self.currency_obj = POOL.get('currency.currency')
        self.address_obj = POOL.get('party.address')

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

    def test_0010_base_pagination(self):
        """
        Test basic pagination
        """
        pagination = BasePagination(1, 3, [])
        self.assertEqual(pagination.count, 0)
        self.assertEqual(pagination.pages, 0)
        self.assertEqual(pagination.begin_count, 0)
        self.assertEqual(pagination.end_count, 0)

        pagination = BasePagination(1, 3, range(1, 10))
        self.assertEqual(pagination.count, 9)
        self.assertEqual(pagination.pages, 3)
        self.assertEqual(pagination.begin_count, 1)
        self.assertEqual(pagination.end_count, 3)
        self.assertEqual(pagination.all_items(), [1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_0020_model_pagination(self):
        """
        Test pagination for models
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            # Create a 100 nereid users
            for id in xrange(0, 100):
                self.nereid_user_obj.create([{
                    'party': self.guest_party,
                    'display_name': 'User %s' % id,
                    'email': 'user-%s@openlabs.co.in' % id,
                    'password': 'password',
                    'company': self.company.id,
                }])

            pagination = Pagination(self.nereid_user_obj, [], 1, 10)
            self.assertEqual(pagination.count, 100)
            self.assertEqual(pagination.pages, 10)
            self.assertEqual(pagination.begin_count, 1)
            self.assertEqual(pagination.end_count, 10)

    def test_0030_model_pagination_serialization(self):
        """
        Test serialization of pagination for models
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            # Create a 100 nereid users
            for id in xrange(0, 100):
                self.nereid_user_obj.create([{
                    'party': self.guest_party,
                    'display_name': 'User %s' % id,
                    'email': 'user-%s@openlabs.co.in' % id,
                    'password': 'password',
                    'company': self.company.id,
                }])

            pagination = Pagination(self.nereid_user_obj, [], 1, 10)
            serialized = pagination.serialize()

            self.assertEqual(serialized['count'], 100)
            self.assertEqual(serialized['pages'], 10)
            self.assertEqual(serialized['page'], 1)
            self.assertEqual(len(serialized['items']), 10)

            self.assert_('display_name' in serialized['items'][0])

    def test_0040_model_pagination_serialization(self):
        """
        Test serialization of pagination for model which does not have
        serialize method
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()

            # Create a 100 addresses
            for id in xrange(0, 100):
                self.address_obj.create([{
                    'party': self.guest_party,
                    'name': 'User %s' % id,
                }])

            pagination = Pagination(self.address_obj, [], 1, 10)
            serialized = pagination.serialize()

            self.assert_('id' in serialized['items'][0])
            self.assert_('rec_name' in serialized['items'][0])

    # TODO: Test the order handling of serialization

if __name__ == '__main__':
    unittest.main()
