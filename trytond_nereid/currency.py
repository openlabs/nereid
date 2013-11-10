# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL
from nereid import request

__all__ = ['Currency']


class Currency(ModelSQL, ModelView):
    '''Currency Manipulation for core.'''
    __name__ = 'currency.currency'

    @classmethod
    def convert(cls, amount):
        """A helper method which converts the amount from the currency of the
        company which owns the current website to the currency of the current
        session.
        """
        return cls.compute(
            request.nereid_website.company.currency,
            amount,
            request.nereid_currency
        )

    @classmethod
    def context_processor(cls):
        """Register compute as convert template context function.

        Usage:
            {{ compute(from_currency, amount, to_currency, round) }}
        Eg: convert
        """
        return {
            'compute': cls.compute,
            'convert': cls.convert
        }
