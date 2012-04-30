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

from nereid.testing import FailFastTextTestRunner
from nereid.contrib.testing import xmlrunner
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
    with open('result.xml', 'wb') as stream:
        xmlrunner.XMLTestRunner(stream).run(suite)

