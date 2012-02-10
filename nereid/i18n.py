# -*- coding: utf-8 -*-
'''

    Internationalisation for Nereid

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details

    WARNING: This is incomplete and is under development

'''
from babel import support
from speaklater import make_lazy_gettext


def get_translations():
    # FIX ME
    #i18n_dir = '/usr/local/tryton/src/nereid-bfa-customisation/i18n'
    #translations = support.Translations.load(i18n_dir, [Transaction().language])
    translations = support.Translations.load()
    translations.gettext = translations.ugettext
    translations.ngettext = translations.ungettext
    return translations


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

_ = make_lazy_gettext(lambda: gettext)
