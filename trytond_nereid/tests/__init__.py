# -*- coding: utf-8 -*-
"""
    __init__

    Nereid Tryton module test cases

    :copyright: (c) 2011-2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
import unittest

import trytond.tests.test_tryton
from test_auth import TestAuth
from test_address import TestAddress
from test_currency import TestCurrency
from test_i18n import TestI18N
from test_static_file import TestStaticFile


def suite():
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAuth)
    )
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestAddress)
    )
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestCurrency)
    )
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestI18N)
    )
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestStaticFile)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
