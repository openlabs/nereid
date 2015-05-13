# -*- coding: utf-8 -*-
"""
    csrf

    :copyright: (c) 2015 by Openlabs Technologies & Consulting (P) Limited
    :license: see LICENSE for more details.
"""
from flask import request
from flask_wtf.csrf import (
    CsrfProtect, validate_csrf, generate_csrf, same_origin
)


__all__ = ['NereidCsrfProtect']


class NereidCsrfProtect(CsrfProtect):

    def init_app(self, app):
        """
        Reimplementation of CsrfProtect.init_app

        By default `init_app` is strictly for Flask and depend on
        `app.view_functions` to `exempt csrf`. But nereid works on
        `request.endpoint`, hence changed the method just to respect
        `request.endpoint` not `app.view_functions`
        """
        app.jinja_env.globals['csrf_token'] = generate_csrf
        app.config.setdefault(
            'WTF_CSRF_HEADERS', ['X-CSRFToken', 'X-CSRF-Token']
        )
        app.config.setdefault('WTF_CSRF_SSL_STRICT', True)
        app.config.setdefault('WTF_CSRF_ENABLED', True)
        app.config.setdefault('WTF_CSRF_METHODS', ['POST', 'PUT', 'PATCH'])

        def _get_csrf_token():
            # find the ``csrf_token`` field in the subitted form
            # if the form had a prefix, the name will be
            # ``{prefix}-csrf_token``
            for key in request.form:
                if key.endswith('csrf_token'):
                    csrf_token = request.form[key]
                    if csrf_token:
                        return csrf_token

            for header_name in app.config['WTF_CSRF_HEADERS']:
                csrf_token = request.headers.get(header_name)
                if csrf_token:
                    return csrf_token
            return None

        # expose csrf_token as a helper in all templates
        @app.context_processor
        def csrf_token():
            return dict(csrf_token=generate_csrf)

        @app.before_request
        def _csrf_protect():
            # many things come from django.middleware.csrf
            if not app.config['WTF_CSRF_ENABLED']:
                return

            if request.method not in app.config['WTF_CSRF_METHODS']:
                return

            if self._exempt_views or self._exempt_blueprints:
                if not request.endpoint:
                    return

                if request.endpoint in self._exempt_views:
                    return
                if request.blueprint in self._exempt_blueprints:
                    return

            if not validate_csrf(_get_csrf_token()):
                reason = 'CSRF token missing or incorrect.'
                return self._error_response(reason)

            if request.is_secure and app.config['WTF_CSRF_SSL_STRICT']:
                if not request.referrer:
                    reason = 'Referrer checking failed - no Referrer.'
                    return self._error_response(reason)

                good_referrer = 'https://%s/' % request.host
                if not same_origin(request.referrer, good_referrer):
                    reason = 'Referrer checking failed - origin not match.'
                    return self._error_response(reason)

            request.csrf_valid = True  # mark this request is csrf valid
