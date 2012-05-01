# -*- coding: utf-8 -*-
"""
    model

    Models to perform tests

    :copyright: (c) 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelSQL, fields
from nereid.backend import ModelPagination

class PaginationModel(ModelPagination, ModelSQL):
    """A Tryton model which uses Pagination which could be used for
    testing."""
    _name = "test_nereid_module.pagination"
    _description = __doc__

    name = fields.Char("Name")

PaginationModel()
