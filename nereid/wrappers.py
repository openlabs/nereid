# -*- coding: UTF-8 -*-
'''
    nereid.wrappers

    Implements the WSGI wrappers

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
from werkzeug.utils import cached_property
from flask.wrappers import Request as RequestBase, Response as ResponseBase
from .globals import current_app, session


class Request(RequestBase):
    "Request Object"

    @cached_property
    def nereid_website(self):
        """Fetch the Browse Record of current website."""
        website_obj = current_app.pool.get('nereid.website')
        website, = website_obj.search([('name', '=', current_app.site)])
        return website_obj.browse(website)

    @cached_property
    def nereid_user(self):
        """Fetch the browse record of current user or None."""
        address_obj = current_app.pool.get('party.address')
        if 'user' not in session:
            if current_app.guest_user:
                return address_obj.browse(current_app.guest_user)
            return None
        return address_obj.browse(session['user'])

    @cached_property
    def nereid_currency(self):
        """Return a browse record for the currency."""
        currency_obj = current_app.pool.get('currency.currency')
        if 'currency' not in session:
            return self.nereid_website.company.currency
        return currency_obj.browse(session['currency'])

    @cached_property
    def nereid_language(self):
        """Return a browse record for the language."""
        lang_obj = current_app.pool.get('ir.lang')
        if 'language' not in session:
            return self.nereid_website.default_language
        return lang_obj.browse(session['language'])

    @cached_property
    def is_guest_user(self):
        """Return true if the user is guest."""
        if current_app.guest_user is None:
            raise RuntimeError("Guest user is not defined for app")
        return ('user' not in session)


class Response(ResponseBase):
    pass
