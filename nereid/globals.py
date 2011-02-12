# -*- coding: utf-8 -*-
"""
    nereid.globals
    ~~~~~~~~~~~~~

    Defines all the global objects that are proxies to the current
    active context.

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from flask.globals import _request_ctx_stack, current_app, request
from flask.globals import session, g
from werkzeug import LocalProxy
from functools import partial


def _lookup_object(name):
    "Gracefully lookup in the request context stack"
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of request context')
    return getattr(top, name)

transaction = LocalProxy(partial(_lookup_object, 'transaction'))

