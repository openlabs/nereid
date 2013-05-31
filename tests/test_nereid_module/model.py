#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from nereid.backend import ModelPagination

class PaginationModel(ModelPagination, ModelSQL):
    """A Tryton model which uses Pagination which could be used for
    testing."""
    _name = "test_nereid_module.pagination"
    _description = __doc__

    name = fields.Char("Name")

PaginationModel()
