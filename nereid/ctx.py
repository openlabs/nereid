# -*- coding: utf-8 -*-
"""
    nereid.ctx
    ~~~~~~~~~

    Implements the objects required to keep the context.

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: GPLv3, see LICENSE for more details.
"""
from flask.ctx import _RequestGlobals, RequestContext as RequestContextBase
from flask.ctx import has_request_context



class RequestContext(RequestContextBase):
    """The request context contains all request relevant information.  It is
    created at the beginning of the request and pushed to the
    `_request_ctx_stack` and removed at the end of it.  It will create the
    URL adapter and request object for the WSGI environment provided.
    """

    def __init__(self, app, environ):
        super(RequestContext, self).__init__(app, environ)
        self.transaction = None
        self.cache = app.cache
