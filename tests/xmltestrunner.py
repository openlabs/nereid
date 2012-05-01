# -*- coding: utf-8 -*-
"""
    test_runner

    A test runner which collects all tests from the core nereid module and
    trytond modules in the directory and executes them

    :copyright: (c) 2011-2012 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from nereid.contrib.testing import xmlrunner

from texttestrunner import suite


if __name__ == '__main__':
    with open('result.xml', 'wb') as stream:
        xmlrunner.XMLTestRunner(stream).run(suite)
