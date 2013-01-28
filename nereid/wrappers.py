# -*- coding: UTF-8 -*-
'''
    nereid.wrappers

    Implements the WSGI wrappers

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
from werkzeug.utils import cached_property
from flask.wrappers import Request as RequestBase, Response as ResponseBase
from flask.helpers import flash
from .globals import current_app, session


def _get_website_name(host):
    """The host could have the host_name and port number. This will try
    to get the best possible guess of the website name from the host name
    """
    #XXX: Needs improvement
    return host.split(':')[0]


class Request(RequestBase):
    "Request Object"

    @cached_property
    def nereid_website(self):
        """Fetch the Browse Record of current website."""
        Website = current_app.pool.get('nereid.website')
        return Website.search([
            ('name', '=', _get_website_name(self.host))]
        )[0]

    @cached_property
    def nereid_user(self):
        """Fetch the browse record of current user or None."""
        NereidUser = current_app.pool.get('nereid.user')
        if 'user' not in session:
            return NereidUser(self.nereid_website.guest_user.id)
        return NereidUser(session['user'])

    @cached_property
    def nereid_currency(self):
        """
        Return a browse record for the currency.
        Currency is looked up first in the language. If it does not exist
        in the language then the currency of the company is returned
        """
        if self.nereid_language.default_currency:
            return self.nereid_language.default_currency
        return self.nereid_website.company.currency

    @cached_property
    def nereid_language(self):
        """Return a browse record for the language."""
        from trytond.transaction import Transaction
        IRLanguage = current_app.pool.get('ir.lang')
        languages = IRLanguage.search([('code', '=', Transaction().language)])
        if not languages:
            flash("We are sorry we don't speak your language yet!")
            return self.nereid_website.default_language
        return languages[0]

    @cached_property
    def is_guest_user(self):
        """Return true if the user is guest."""
        return ('user' not in session)


class Response(ResponseBase):
    pass
