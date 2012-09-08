# -*- coding: utf-8 -*-
"""
    i18n

    Internationalisation of the application. This is usually useful to
    translate the template files and date and number formatting in templates.

    :copyright: (c) 2011-2012 by Openlabs Technologies & Consulting (P) Limited
    :copyright: (c) 2010 by Armin Ronacher.
    :license: GPLv3, see LICENSE for more details.
"""
import flaskext.babel
from flaskext.babel import Babel
from babel import support, Locale
from pytz import timezone
from nereid.globals import _request_ctx_stack


def get_translations():
    """Returns the correct gettext translations that should be used for
    this request.  This will never fail and return a dummy translation
    object if used outside of the request or if a translation cannot be
    found.
    """
    ctx = _request_ctx_stack.top
    if ctx is None:
        return None
    translations = getattr(ctx, 'babel_translations', None)
    if translations is None and ctx.app.translations_path:
        dirname = ctx.app.translations_path
        translations = support.Translations.load(dirname, [get_locale()])
        ctx.babel_translations = translations
    return translations


flaskext.babel.get_translations = get_translations


def get_locale():
    """Returns the locale that should be used for this request as
    `babel.Locale` object.  This returns `None` if used outside of
    a request.
    """
    ctx = _request_ctx_stack.top
    if ctx is None:
        return None
    locale = getattr(ctx, 'babel_locale', None)

    if locale is None:
        babel = ctx.app.extensions['babel']
        if babel.locale_selector_func is None:
            # Try to use the 
            rv = ctx.request.nereid_language.code
        else:
            rv = babel.locale_selector_func()

        if rv is None:
            locale = babel.default_locale
        else:
            locale = Locale.parse(rv)
        ctx.babel_locale = locale
    return locale

flaskext.babel.get_locale = get_locale


def get_timezone():
    """Returns the timezone that should be used for this request as
    `pytz.timezone` object.  This returns `None` if used outside of
    a request.
    """
    ctx = _request_ctx_stack.top
    tzinfo = getattr(ctx, 'babel_tzinfo', None)
    if tzinfo is None:
        babel = ctx.app.extensions['babel']
        if babel.timezone_selector_func is None:
            tzinfo = ctx.request.nereid_website.timezone
            if ctx.request.nereid_user.timezone:
                tzinfo = timezone(ctx.request.nereid_user.timezone)
        else:
            rv = babel.timezone_selector_func()
            if rv is None:
                tzinfo = babel.default_timezone
            else:
                if isinstance(rv, basestring):
                    tzinfo = timezone(rv)
                else:
                    tzinfo = rv
        ctx.babel_tzinfo = tzinfo
    return tzinfo

flaskext.babel.get_timezone = get_timezone
