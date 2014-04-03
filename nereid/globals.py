# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from flask.globals import (_request_ctx_stack, current_app,  # noqa
    request, session, g, LocalProxy, _find_app)
from flask.ext.login import current_user                     # noqa


def _find_cache():
    """
    The application context will be automatically handled by
    _find_app method in flask
    """
    app = _find_app()
    return app.cache

cache = LocalProxy(_find_cache)
