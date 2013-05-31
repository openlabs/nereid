# -*- coding: utf-8 -*-
"""
    __init__

    A test module to test core nereid features where Tryton model is reqd

    :copyright: (c) 2011-2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.pool import Pool
from model import PaginationModel


def register():
    """
    This function will register test nereid module
    """
    Pool.register(
        PaginationModel,
        module='test_nereid_module', type_='model',
    )
