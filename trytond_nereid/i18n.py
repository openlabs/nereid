# -*- coding: utf-8 -*-
'''

    Internationalisation for Nereid

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details

    WARNING: This is incomplete and is under development

'''
from __future__ import absolute_import
import os
import logging

from babel import support
from speaklater import is_lazy_string, make_lazy_string

from trytond.transaction import Transaction

_translations = {}
logger = logging.getLogger('nereid.i18n')
logger.setLevel(logging.DEBUG)


def get_translations():
    """
    Load the translations and return a Translation object. This method is
    designed not to fail
    """
    translations = support.Translations.load()
    if not hasattr(_translations, Transaction().language):
        i18n_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'i18n'
        )
        logger.debug("Load translations from %s" % i18n_dir)
        translations = support.Translations.load(
            i18n_dir, [Transaction().language]
        )
        # Monkey patch gettext and ngettext to appect only unicode
        # This is required for WTForms
        translations.gettext = translations.ugettext
        translations.ngettext = translations.ungettext

    return _translations.setdefault(Transaction().language, translations)


def gettext(string, **variables):
    """Translates a string with the current locale and passes in the
    given keyword arguments as mapping to a string formatting string.

    ::

        gettext(u'Hello World!')
        gettext(u'Hello %(name)s!', name='World')
    """
    t = get_translations()
    if t is None:
        return string % variables
    return t.ugettext(string) % variables


def ngettext(singular, plural, n, **variables):
    """Translates a string with the current locale and passes it to the
    ngettext API of the translations object
    """
    t = get_translations()
    variables.setdefault('num', n)
    if t is None:
        return (plural if n > 1 else singular) % variables
    return t.ungettext(singular, plural, n) % variables


def make_lazy_gettext(lookup_func):
    """Creates a lazy gettext function dispatches to a gettext
    function as returned by `lookup_func`.

    :copyright: (c) 2010 by Armin Ronacher.

    Example:

    >>> translations = {u'Yes': u'Ja'}
    >>> lazy_gettext = make_lazy_gettext(lambda: translations.get)
    >>> x = lazy_gettext(u'Yes')
    >>> x
    lu'Ja'
    >>> translations[u'Yes'] = u'Si'
    >>> x
    lu'Si'
    """
    def lazy_gettext(string, *args, **kwargs):
        if is_lazy_string(string):
            return string
        return make_lazy_string(lookup_func(), string, *args, **kwargs)
    return lazy_gettext

_, N_ = make_lazy_gettext(lambda: gettext), make_lazy_gettext(lambda: ngettext)
