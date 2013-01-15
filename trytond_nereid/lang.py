# -*- coding: utf-8 -*-
"""
    lang

    Language

    :copyright: © 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, fields


class Language(ModelSQL, ModelView):
    _name = "ir.lang"

    default_currency = fields.Many2One(
        'currency.currency', 'Default Currency'
    )

Language()
