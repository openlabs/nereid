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

from nereid.templating import ModuleTemplateLoader
from jinja2.ext import babel_extract, GETTEXT_FUNCTIONS
from trytond.pool import Pool, PoolMeta
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

__metaclass__ = PoolMeta


class Translation:
    __name__ = 'ir.translation'

    @classmethod
    def __setup__(cls):
        super(Translation, cls).__setup__()
        new_type = ('nereid_template', 'Nereid Template')
        if new_type not in cls.type.selection:
            cls.type.selection.append(new_type)
        new_type = ('nereid_form', 'Nereid Form')
        if new_type not in cls.type.selection:
            cls.type.selection.append(new_type)


class TranslationSet:
    __name__ = 'ir.translation.set'

    def transition_set_(self):
        state = super(TranslationSet, self).transition_set_()
        self.set_nereid_templates()
        self.set_nereid_forms()
        return state

    def set_nereid_templates(self):
        " Loads all nereid templates translatable strings into the database "
        pool = Pool()
        Translation = pool.get('ir.translation')
        to_create = []
        for template, lineno, message in self.get_nereid_template_strings():
            translations = Translation.search([
                    ('lang', '=', 'en_US'),
                    ('type', '=', 'nereid_template'),
                    ('name', '=', template),
                    ('src', '=', message),
                    ], limit=1)
            if translations:
                continue
            to_create.append({
                    'name': template,
                    'res_id': lineno,
                    'lang': 'en_US',
                    'src': message,
                    'type': 'nereid_template',
                    #TODO: Get the module for the template
                    'module': 'nereid',
                    })
        if to_create:
            Translation.create(to_create)

    def get_nereid_template_strings(self):
        """
        Returns a list of (template, lineno, message) for all the translatable
        templates in the installed modules
        """
        loader = ModuleTemplateLoader()
        res = []
        for template in loader.list_templates():
            _, filename, _ = loader.get_source({}, template)
            with open(filename) as fileobj:
                for lineno, funcname, message, comments in babel_extract(
                        fileobj, GETTEXT_FUNCTIONS, {}, {}):
                    res.append((template, lineno, message,))
        return res

    def set_nereid_forms(self):
        " Loads all nereid forms translatable strings into the database "
        #TODO
        pass
