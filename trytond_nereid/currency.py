# -*- coding: utf-8 -*-
"""
    currency

    Currency handling at core level

    :copyright: © 2011-2012 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelView, ModelSQL
from nereid import request

class Currency(ModelSQL, ModelView):
    '''Currency Manipulation for core.'''
    _name = 'currency.currency'

    def convert(self, amount):
        """A helper method which converts the amount from the currency of the
        company which owns the current website to the currency of the current
        session.
        """
        return self.compute(
            request.nereid_website.company.currency.id,
            amount,
            request.nereid_currency.id)

    def context_processor(self):
        """Register compute as convert template context function.

        Usage:
            {{ compute(from_currency, amount, to_currency, round) }}
        Eg: convert
        """
        return {
            'compute': self.compute,
            'convert': self.convert
            }

Currency()
