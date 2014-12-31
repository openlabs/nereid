# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from model import TestModel


def register():
    """
    This function will register test nereid module
    """
    Pool.register(
        TestModel,
        module='nereid_test', type_='model',
    )
