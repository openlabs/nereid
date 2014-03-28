# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import trytond.tests.test_tryton    # noqa

from nereid.tests import suite as nereid_test_suite
from trytond_nereid.tests import suite as trytond_nereid_test_suite


def suite():
    combined_test_suite = unittest.TestSuite([
        nereid_test_suite(),
        trytond_nereid_test_suite(),
    ])
    return combined_test_suite
