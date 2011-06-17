# -*- coding: utf-8 -*-
"""
    test_runner

    A test runner which collects all tests from the core nereid module and
    trytond modules in the directory and executes them

    As tryton itslef is not a dependency of nereid, the tryton tests will be 
    loaded, only if tryton is installed

    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import unittest2

try:
    import trytond
    TRYTON_INSTALLED = True
except ImportError:
    TRYTON_INSTALLED = False

# Test Suite into which all tests are collected
suite = unittest2.TestSuite()

# Begin loading tests
if TRYTON_INSTALLED:
    # First load a configuration to do the test
    from trytond.config import CONFIG

    CONFIG.parse() 
    print CONFIG.options

    # Now load all modules
    from trytond.modules import register_classes
    register_classes()

    # Run this specific test suite
    from trytond.modules.nereid.tests import suite as _suite
    suite.addTests([_suite()])


if __name__ == '__main__':
    unittest2.TextTestRunner(verbosity=2).run(suite)
