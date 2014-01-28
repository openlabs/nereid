#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

    Test the Internationalisation

    :copyright: (c) 2012-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from nereid.testing import NereidTestCase
from nereid import render_template
from trytond.transaction import Transaction
from nereid.contrib.locale import make_lazy_gettext, make_lazy_ngettext

_ = make_lazy_gettext('nereid')
ngettext = make_lazy_ngettext('nereid')


class TestI18N(NereidTestCase):
    """
    Test the internationalisation
    """

    def setUp(self):
        trytond.tests.test_tryton.install_module('nereid_test')

        self.nereid_website_obj = POOL.get('nereid.website')
        self.nereid_website_locale_obj = POOL.get('nereid.website.locale')
        self.nereid_permission_obj = POOL.get('nereid.permission')
        self.nereid_user_obj = POOL.get('nereid.user')
        self.url_map_obj = POOL.get('nereid.url_map')
        self.company_obj = POOL.get('company.company')
        self.currency_obj = POOL.get('currency.currency')
        self.language_obj = POOL.get('ir.lang')
        self.party_obj = POOL.get('party.party')

    def setup_defaults(self):
        """
        Setup the defaults
        """
        usd, eur = self.currency_obj.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }, {
            'name': 'Euro',
            'code': 'EUR',
            'symbol': '€',
        }])
        self.party, = self.party_obj.create([{
            'name': 'Openlabs',
        }])
        self.company, = self.company_obj.create([{
            'party': self.party,
            'currency': usd,
        }])
        self.guest_party, = self.party_obj.create([{
            'name': 'Guest User',
        }])
        self.guest_user, = self.nereid_user_obj.create([{
            'party': self.guest_party,
            'display_name': 'Guest User',
            'email': 'guest@openlabs.co.in',
            'password': 'password',
            'company': self.company.id,
        }])
        url_map_id, = self.url_map_obj.search([], limit=1)
        en_us, = self.language_obj.search([('code', '=', 'en_US')])
        fr_fr, = self.language_obj.search([('code', '=', 'fr_FR')])
        usd, = self.currency_obj.search([('code', '=', 'USD')])
        locale, = self.nereid_website_locale_obj.create([{
            'code': 'en_US',
            'language': en_us,
            'currency': usd,
        }])
        locale_fr_FR, = self.nereid_website_locale_obj.create([{
            'code': 'fr_FR',
            'language': fr_fr,
            'currency': eur,
        }])
        self.nereid_website_obj.create([{
            'name': 'localhost',
            'url_map': url_map_id,
            'company': self.company.id,
            'application_user': USER,
            'default_locale': locale,
            'locales': [('add', [locale.id, locale_fr_FR.id])],
            'guest_user': self.guest_user.id,
        }])

    def set_translations(self):
        """
        Sets the translations
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')

        session_id, _, _ = TranslationSet.create()
        set_wizard = TranslationSet(session_id)
        set_wizard.transition_set_()

    def update_translations(self, language_code):
        """
        Update the translations for the language
        """
        TranslationUpdate = POOL.get('ir.translation.update', type='wizard')
        IRLanguage = POOL.get('ir.lang')

        session_id, _, _ = TranslationUpdate.create()
        update_wizard = TranslationUpdate(session_id)

        # set fr_FR  as translatable
        language, = IRLanguage.search([
            ('code', '=', language_code)
        ], limit=1)
        language.translatable = True
        language.save()

        update_wizard.start.language = language
        update_wizard.do_update(update_wizard.update.get_action())

    def get_template_source(self, name):
        """
        Return templates
        """
        templates = {
            'home.jinja': '{{get_flashed_messages()}}',
        }
        return templates.get(name)

    def test_0010_simple_txn(self):
        """
        Test if the translations work in a simple env
        """
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            s = _("en_US")
            self.assertEqual(s, u'en_US')

            # install translations
            self.set_translations()
            self.update_translations('fr_FR')

            # without setting a tranlsation looking for it gives en_US
            with Transaction().set_context(language="fr_FR"):
                self.assertEqual(s, u'en_US')

            # write a translation for it
            translation, = IRTranslation.search([
                ('module', '=', 'nereid'),
                ('src', '=', 'en_US'),
                ('lang', '=', 'fr_FR')
            ])
            translation.value = 'fr_FR'
            translation.save()

            with Transaction().set_context(language="fr_FR"):
                self.assertEqual(s, u'fr_FR')

    def test_0020_kwargs(self):
        """
        Test if kwargs work
        """
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            s = _("Hi %(name)s", name="Sharoon")
            self.assertEqual(s, u"Hi Sharoon")

            # install translations
            self.set_translations()
            self.update_translations('fr_FR')

            # without setting a tranlsation looking for it gives en_US
            with Transaction().set_context(language="fr_FR"):
                self.assertEqual(s, u'Hi Sharoon')

            # write a translation for it
            translation, = IRTranslation.search([
                ('module', '=', 'nereid'),
                ('src', '=', 'Hi %(name)s'),
                ('lang', '=', 'fr_FR')
            ])
            translation.value = 'Bonjour %(name)s'
            translation.save()

            with Transaction().set_context(language="fr_FR"):
                self.assertEqual(s, u'Bonjour Sharoon')

    def test_0030_ngettext(self):
        """
        Test if ngettext work
        """
        IRTranslation = POOL.get('ir.translation')

        singular = ngettext("%(num)d apple", "%(num)d apples", 1)
        plural = ngettext("%(num)d apple", "%(num)d apples", 2)

        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.assertEqual(singular, u"1 apple")
            self.assertEqual(plural, u"2 apples")

            # install translations
            self.set_translations()
            self.update_translations('fr_FR')

            # without setting a tranlsation looking for it gives en_US
            with Transaction().set_context(language="fr_FR"):
                self.assertEqual(singular, u"1 apple")
                self.assertEqual(plural, u"2 apples")

            # write a translation for singular
            translations = IRTranslation.search([
                ('module', '=', 'nereid'),
                ('src', '=', '%(num)d apple'),
                ('lang', '=', 'fr_FR')
            ])
            for translation in translations:
                translation.value = '%(num)d pomme'
                translation.save()

            # write a translation for it
            translations = IRTranslation.search([
                ('module', '=', 'nereid'),
                ('src', '=', '%(num)d apples'),
                ('lang', '=', 'fr_FR')
            ])
            for translation in translations:
                translation.value = '%(num)d pommes'
                translation.save()

            with Transaction().set_context(language="fr_FR"):
                self.assertEqual(singular, u"1 pomme")
                self.assertEqual(plural, u"2 pommes")

    def test_0110_template(self):
        """
        Test the working of translations in templates
        """
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            class User(object):
                def __init__(self, username):
                    self.username = username

                def __html__(self):
                    return self.username

            user = User('Sharoon')

            template_context = {
                'user': user,
                'username': user.username,
                'list': [1],
                'objname': _('name'),
                'apples': [1, 2],
            }

            def check_en_us(rv):
                self.assertTrue('There is 1 name object.' in rv)
                self.assertTrue('2 apples' in rv)
                self.assertTrue('<p>Hello Sharoon!</p>' in rv)

            def check_fr_fr(rv):
                self.assertTrue('There is 1 name in fr_FR object.' in rv)
                self.assertTrue('2 pommes' in rv)
                self.assertTrue('<p>Bonjour Sharoon!</p>' in rv)

            with app.test_request_context('/en_US/'):
                rv = unicode(render_template(
                    'tests/translation-test.html',
                    **template_context
                ))
                check_en_us(rv)

                with Transaction().set_context(language="fr_FR"):
                    # No translations set yet, so same thing
                    rv = unicode(render_template(
                        'tests/translation-test.html',
                        **template_context
                    ))
                    check_en_us(rv)

            # install translations
            self.set_translations()
            self.update_translations('fr_FR')

            # write french translations
            translation, = IRTranslation.search([
                ('module', '=', 'nereid_test'),
                ('type', '=', 'nereid_template'),
                ('src', '=', 'Hello %(username)s!'),
                ('lang', '=', 'fr_FR')
            ])
            translation.value = 'Bonjour %(username)s!'
            translation.save()

            translation, = IRTranslation.search([
                ('module', '=', 'nereid_test'),
                ('type', '=', 'nereid_template'),
                ('src', '=', '%(num)d apples'),
                ('lang', '=', 'fr_FR')
            ])
            translation.value = '%(num)d pommes'
            translation.save()

            translation, = IRTranslation.search([
                ('module', '=', 'nereid_test'),
                ('type', '=', 'nereid_template'),
                ('src', '=', 'Hello %(name)s!'),
                ('lang', '=', 'fr_FR')
            ])
            translation.value = 'Bonjour %(name)s!'
            translation.save()

            translation, = IRTranslation.search([
                ('module', '=', 'nereid'),
                ('name', '=', 'tests/test_i18n.py'),
                ('src', '=', 'name'),
                ('lang', '=', 'fr_FR')
            ])
            translation.value = 'name in fr_FR'
            translation.save()

            with app.test_request_context('/fr_FR/'):
                with Transaction().set_context(language="fr_FR"):
                    rv = unicode(render_template(
                        'tests/translation-test.html',
                        **template_context
                    ))
                    check_fr_fr(rv)


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestI18N)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
