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
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
