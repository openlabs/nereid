# -*- coding: utf-8 -*-
"""
    testrunner

    A regular test runner which outputs results to stdout.

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: GPLv3, see LICENSE for more details.
"""
import unittest2
from trytond.config import CONFIG

CONFIG.options['db_type'] = 'sqlite'
CONFIG.options['data_path'] = '/tmp/temp_tryton_data/'

from trytond.modules import register_classes
register_classes()

# Test Suite into which all tests are collected
suite = unittest2.TestSuite()

from trytond.modules.nereid.tests import suite as _suite
suite.addTests([_suite()])


if __name__ == '__main__':
    unittest2.TextTestRunner(verbosity=2).run(suite)
