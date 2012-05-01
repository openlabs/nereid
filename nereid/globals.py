# -*- coding: utf-8 -*-
"""
    nereid.globals
    ~~~~~~~~~~~~~

    Defines all the global objects that are proxies to the current
    active context.

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: GPLv3, see LICENSE for more details.
"""
from flask.globals import (_request_ctx_stack, current_app,
    request, _lookup_object, session, g, LocalProxy)


def _find_cache():
    """The application context will be automatically handled by
    _find_app method in flask
    """
    try:
        from flask.globals import _find_app
        app = _find_app()
    except ImportError:
        # Flask < 0.9
        app = _lookup_object('app')
    return app.cache

cache = LocalProxy(_find_cache)
