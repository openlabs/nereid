# -*- coding: UTF-8 -*-
'''
    nereid.wrappers

    Implements the WSGI wrappers

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''

from flask.wrappers import Request as RequestBase, Response as ResponseBase
from .globals import current_app, session


class Request(RequestBase):
    "Request Object"

    @property
    def nereid_website(self):
        """
        Fetch the Browse Record of current website
        """
        website_obj = current_app.pool.get('nereid.website')
        website, = website_obj.search([('name', '=', current_app.site)])
        return website_obj.browse(website)

    @property
    def nereid_user(self):
        """
        Fetch the browse record of current user or None
        """
        if 'user' not in session:
            return None

        address_obj = current_app.pool.get('party.address')
        return address_obj.browse(session['user'])


class Response(ResponseBase):
    pass
