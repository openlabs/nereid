# -*- coding: utf-8 -*-
"""
    __init__

    Nereid Tryton module test cases

    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest2 as unittest

from test_auth import TestAuth 
from test_address import TestAddress
from test_currency import TestCurrency
from test_i18n import TestI18N

def suite():
    suite = unittest.TestSuite()
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAuth)
    )
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAddress)
    )
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency)
    )
    suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestI18N)
    )
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
