# -*- coding: utf-8 -*-
"""
    test_pagination

    Test the pagination feature by polling actual data

    :copyright: © 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import sys, os
DIR = os.path.abspath(os.path.normpath(os.path.join(__file__,
    '..', '..', '..', '..', '..', 'trytond')))
if os.path.isdir(DIR):
    sys.path.insert(0, os.path.dirname(DIR))
import unittest2 as unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view
from trytond.transaction import Transaction
from nereid.backend import Pagination


class PaginationTestCase(unittest.TestCase):
    """Test the pagination feature.
    """

    def create_records(self, count=100, start_index=1):
        """Created given number of records. This function requires to be called
        inside the transaction context

        :return: created ids
        """
        ids = []
        for iteration in xrange(start_index, start_index + count):
            ids.append(self.test_obj.create({
                'name': 'record-%s' % iteration
                }))
        return ids

    def setUp(self):
        trytond.tests.test_tryton.install_module('test_nereid_module')

        self.test_obj = POOL.get('test_nereid_module.pagination')

    def test_0010_returned_object(self):
        """Test if calling paginate method returns a pagination object"""
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            rv = self.test_obj.paginate([], 1, error_out=False)
            self.assertTrue(isinstance(rv, Pagination))

            transaction.cursor.rollback()

    def test_0020_error_out(self):
        """Ensure that error_out feature works"""
        from werkzeug.exceptions import NotFound
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            self.assertRaises(
                NotFound,
                self.test_obj.paginate, ([], 1), {'error_out': True})

            transaction.cursor.rollback()

    def test_0030_count(self):
        """Test that the total count is correct"""
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            ids = self.create_records(100)

            # Without Domain
            rv = self.test_obj.paginate([], 1)
            self.assertEqual(rv.count, 100)

            # With ids only domain
            rv = self.test_obj.paginate([('id', 'in', ids)], 1)
            self.assertEqual(rv.count, 100)

            transaction.cursor.rollback()

    def test_0040_all_items(self):
        """Test there are 100 items returned"""
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            ids = self.create_records(100)

            # Without Domain
            rv = self.test_obj.paginate([], 1, error_out=False)
            self.assertEqual(len(rv.all_items()), 100)

            # With ids only domain
            rv = self.test_obj.paginate([('id', 'in', ids)], 1)
            self.assertEqual(len(rv.all_items()), 100)

            transaction.cursor.rollback()

    def test_0050_items_and_pages(self):
        """Items and pages"""
        with Transaction().start(DB_NAME, USER, CONTEXT) as transaction:
            ids = self.create_records(100)

            # Without Domain
            rv = self.test_obj.paginate([], 1, error_out=False)
            self.assertEqual(len(rv.items()), 20)
            self.assertEqual(rv.pages, 5)
            # Last Page
            rv = self.test_obj.paginate([], 5, error_out=False)
            self.assertEqual(len(rv.items()), 20)
            self.assertEqual(rv.pages, 5)
            # Invalid Page
            rv = self.test_obj.paginate([], 6, error_out=False)
            self.assertEqual(len(rv.items()), 0)
            self.assertEqual(rv.pages, 5)

            # With ids only domain
            rv = self.test_obj.paginate([('id', 'in', ids)], 1)
            self.assertEqual(len(rv.items()), 20)
            self.assertEqual(rv.pages, 5)
            # Last Page
            rv = self.test_obj.paginate([('id', 'in', ids)], 5)
            self.assertEqual(len(rv.items()), 20)
            self.assertEqual(rv.pages, 5)
            # Invalid Page
            rv = self.test_obj.paginate([('id', 'in', ids)], 6, error_out=False)
            self.assertEqual(len(rv.items()), 0)
            self.assertEqual(rv.pages, 5)

            transaction.cursor.rollback()


def get_suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        PaginationTestCase
    ))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(get_suite())
