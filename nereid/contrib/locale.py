# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import gettext

import flask.ext.babel
from speaklater import is_lazy_string, make_lazy_string
from flask.ext.babel import Babel  # noqa
from babel import Locale
from pytz import timezone
from nereid.globals import _request_ctx_stack
from trytond.pool import Pool
from trytond.transaction import Transaction


class TrytonTranslations(gettext.NullTranslations, object):
    """
    An extended translation catalog class that uses tryton's
    IRTranslation system.

    The ttype in tryton ir.translation works more like a message domain and
    hence the domain in the catalog represents one of the ttypes introduced
    by nereid.

    .. note::

        The ir.translation module does not have the capability to handle
        ngettext well as there is no option to have multiple strings. The
        extraction system will create each message separately.
    """

    def __init__(self, module, ttype='nereid'):
        self.module = module
        self.plural = lambda n: int(n != 1)
        self.ttype = ttype
        super(TrytonTranslations, self).__init__(fp=None)

    def ugettext(self, message):
        """Translates a string with the current locale
        ::

            gettext(u'Hello World!')
        """
        IRTranslation = Pool().get('ir.translation')

        rv = IRTranslation.get_translation_4_nereid(
            self.module, self.ttype, Transaction().language, message
        )
        return (rv or message)

    def lazy_ugettext(self, message, **variables):
        """Translates a string with the current locale and passes in the
        given keyword arguments as mapping to a string formatting string.

        ::

            lazy_ugettext(u'Hello World!')
            lazy_ugettext(u'Hello %(name)s!', name='World')
        """
        return self.ugettext(message) % variables

    def ungettext(self, singular, plural, n, **variables):
        """
        Translates a string with the current locale
        """
        IRTranslation = Pool().get('ir.translation')

        if self.plural(n):
            message = plural
        else:
            message = singular
        rv = IRTranslation.get_translation_4_nereid(
            self.module, self.ttype, Transaction().language, message
        )
        return (rv or message)

    def lazy_ungettext(self, singular, plural, n, **variables):
        """Translates a string with the current locale and passes in the
        given keyword arguments as mapping to a string formatting string.
        The `num` parameter is used to dispatch between singular and various
        plural forms of the message.  It is available in the format string
        as ``%(num)d`` or ``%(num)s``.  The source language should be
        English or a similar language which only has one plural form.

        ::

            lazy_ungettext(u'%(num)d Apple', u'%(num)d Apples', num=len(apples))
        """
        variables.setdefault('num', n)
        return self.ugettext(
            self.ungettext(singular, plural, n)
        ) % variables

    gettext = ugettext
    ngettext = ungettext


def get_translations():
    """
    Returns the correct gettext translations that should be used for
    this request.  This will never fail and return a dummy translation
    object if used outside of the request or if a translation cannot be
    found.
    """
    ctx = _request_ctx_stack.top
    if ctx is None:
        return None
    translations = getattr(ctx, 'babel_translations', None)
    if translations is None:
        translations = TrytonTranslations(module=None, ttype='nereid_template')
        ctx.babel_translations = translations
    return translations


flask.ext.babel.get_translations = get_translations


def get_locale():
    """
    Returns the locale that should be used for this request as
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
            rv = ctx.request.nereid_language.code
        else:
            rv = babel.locale_selector_func()

        if rv is None:
            locale = babel.default_locale
        else:
            locale = Locale.parse(rv)
        ctx.babel_locale = locale
    return locale

flask.ext.babel.get_locale = get_locale


def get_timezone():
    """
    Returns the timezone that should be used for this request as
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

flask.ext.babel.get_timezone = get_timezone


def make_lazy_gettext(module):
    """
    Given a module name, return a lazy gettext function which is
    lazily evaluated.

    A typical usage pattern would be::

        from nereid.contrib.i18n import make_lazy_gettext

        _ = make_lazy_gettext('module_name')

    """
    def lazy_gettext(string, **variables):
        if is_lazy_string(string):
            return string
        translations = TrytonTranslations(module, 'nereid')
        return make_lazy_string(
            translations.lazy_ugettext, string, **variables
        )
    return lazy_gettext


def make_lazy_ngettext(module):
    """
    Given a module name, return a lazy gettext function which is
    lazily evaluated.

    A typical usage pattern would be::

        from nereid.contrib.i18n import make_lazy_gettext

        ngettext = make_lazy_ngettext('module_name')

    """
    def lazy_gettext(singular, plural, number, **variables):
        translations = TrytonTranslations(module, 'nereid')
        return make_lazy_string(
            translations.lazy_ungettext, singular, plural, number, **variables
        )
    return lazy_gettext
