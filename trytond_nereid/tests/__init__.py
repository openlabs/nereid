# -*- coding: utf-8 -*-
"""
    __init__

    Nereid Tryton module test cases

    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from unittest import TestSuite

from .test_configuration import suite as configuration_test_suite
from .test_currency import suite as currency_test_suite
from .test_language import suite as language_test_suite

def suite():
    suite_ = TestSuite()
    suite_.addTests([
        configuration_test_suite(),
        currency_test_suite(),
        language_test_suite(),
        ])
    return suite_
