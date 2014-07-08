# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL
from nereid import request, context_processor

__all__ = ['Currency']


class Currency(ModelSQL, ModelView):
    '''Currency Manipulation for core.'''
    __name__ = 'currency.currency'

    @classmethod
    @context_processor('convert')
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
    @context_processor('compute')
    def compute(cls, from_currency, amount, to_currency, round=True):
        """Adds compute method to context processors"""
        return super(Currency, cls).compute(from_currency, amount, to_currency)
