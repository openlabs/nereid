# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction
from nereid.testing import NereidTestCase


class TestTranslation(NereidTestCase):
    'Test Translation'

    def setUp(self):
        # Install the test module which has bundled translations which can
        # be used for this test
        trytond.tests.test_tryton.install_module('nereid_test')

    def test_0010_nereid_template_extraction(self):
        """
        Test translation extaction from nereid templates
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            count_before = IRTranslation.search([
                ('type', '=', 'nereid_template')
            ], count=True)
            self.assertEqual(count_before, 0)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            count_after = IRTranslation.search([
                ('type', '=', 'nereid_template')
            ], count=True)

            self.assertTrue(count_after > count_before)

    def test_0020_nereid_code_extraction(self):
        """
        Ensure that templates are extracted from the code
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            count_before = IRTranslation.search([
                ('type', '=', 'nereid')
            ], count=True)
            self.assertEqual(count_before, 0)

            # Set the nereid translations alone
            set_wizard.set_nereid()

            count_after = IRTranslation.search([
                ('type', '=', 'nereid')
            ], count=True)

            self.assertTrue(count_after > count_before)

    def test_0030_wtforms_builtin_extraction(self):
        """
        Ensure that the builtin messages from wtforms are also extracted
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            count_before = IRTranslation.search([
                ('type', '=', 'wtforms')
            ], count=True)
            self.assertEqual(count_before, 0)

            # Set the wtforms translations alone
            set_wizard.set_wtforms()

            count_after = IRTranslation.search([
                ('type', '=', 'wtforms')
            ], count=True)

            self.assertTrue(count_after > count_before)

    def test_0040_template_gettext_using_(self):
        """
        Test for gettext without comment using _
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            # gettext with no comments and using _
            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', 'gettext')
            ])
            self.assertEqual(translation.comments, None)
            self.assertEqual(translation.res_id, 7)

    def test_0050_template_gettext_2(self):
        """
        Test for gettext with comment before it
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', 'gettext with comment b4')
            ])
            self.assertEqual(translation.comments, translation.src)
            self.assertEqual(translation.res_id, 10)

    def test_0060_template_gettext_3(self):
        """
        Test for gettext with comment inline
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', 'gettext with comment inline')
            ])
            self.assertEqual(translation.comments, translation.src)
            self.assertEqual(translation.res_id, 12)

    def test_0070_template_gettext_4(self):
        """
        Test for gettext using gettext instead of _
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', 'Hello World!')
            ])
            self.assertEqual(translation.comments, None)
            self.assertEqual(translation.res_id, 17)

    def test_0080_template_ngettext(self):
        """
        Test for ngettext
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', '%(num)d apple')
            ])
            self.assertEqual(translation.res_id, 20)

            # Look for plural
            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', '%(num)d apples')
            ])
            self.assertEqual(translation.res_id, 20)

    def test_0090_template_trans_tag(self):
        """
        Test for {% trans %}Hola {{ user }}!{% endtrans %} tag

        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            # XXX: See how {{ user }} changed to %(user)s
            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', 'Hello %(username)s!'),
            ])
            self.assertEqual(
                translation.comments, 'Translation with trans tag'
            )
            self.assertEqual(translation.res_id, 23)

    def test_0100_template_trans_tag_with_expr(self):
        """
        Test for
        {% trans user=user.username %}Hello {{ user }}!{% endtrans %} tag
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            # XXX: See how {{ user }} changed to %(user)s
            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', '=', 'Hello %(name)s!')
            ])
            self.assertEqual(
                translation.comments, 'Translation with an expression'
            )
            self.assertEqual(translation.res_id, 26)

    def test_0110_template_trans_tag_plural(self):
        """
        Test for

        {% trans count=list|length %}
        There is {{ count }} {{ name }} object.
        {% pluralize %}
        There are {{ count }} {{ name }} objects.
        {% endtrans %}

        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        IRTranslation = POOL.get('ir.translation')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)

            # Set the nereid_template translations alone
            set_wizard.set_nereid_template()

            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', 'ilike', '%There is %(count)s %(objname)s object.%'),
            ])
            self.assertEqual(
                translation.comments, 'trans tag with pluralisation'
            )
            self.assertEqual(translation.res_id, 29)

            # now look for the plural
            translation, = IRTranslation.search([
                ('type', '=', 'nereid_template'),
                ('module', '=', 'nereid_test'),
                ('src', 'ilike', '%There are %(count)s %(objname)s objects.%'),
            ])
            self.assertEqual(
                translation.comments, 'trans tag with pluralisation'
            )
            self.assertEqual(translation.res_id, 29)

    def test_0200_translation_clean(self):
        """
        Check if the cleaning of translations work
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        TranslationClean = POOL.get('ir.translation.clean', type='wizard')
        IRTranslation = POOL.get('ir.translation')
        IRModule = POOL.get('ir.module.module')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            # First create all the translations
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)
            set_wizard.transition_set_()

            # Uninstall nereid_test and there should be no translations
            # belonging to that module with type as nereid or
            # nereid_template
            nereid_test, = IRModule.search([('name', '=', 'nereid_test')])
            nereid_test.state = 'uninstalled'
            nereid_test.save()

            session_id, _, _ = TranslationClean.create()
            clean_wizard = TranslationClean(session_id)
            clean_wizard.transition_clean()

            count = IRTranslation.search([
                ('module', '=', 'nereid_test'),
                ('type', 'in', ('nereid', 'nereid_template'))
            ], count=True)
            self.assertEqual(count, 0)

    def test_0300_translation_update(self):
        """
        Check if the update does not break this functionality
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        TranslationUpdate = POOL.get('ir.translation.update', type='wizard')
        IRTranslation = POOL.get('ir.translation')
        IRLanguage = POOL.get('ir.lang')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            # First create all the translations
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)
            set_wizard.transition_set_()

            # set an additional language as translatable
            new_lang, = IRLanguage.search([
                ('translatable', '=', False)
            ], limit=1)
            new_lang.translatable = True
            new_lang.save()

            count_before = IRTranslation.search([], count=True)

            # Now update the translations
            session_id, _, _ = TranslationUpdate.create()
            update_wizard = TranslationUpdate(session_id)

            update_wizard.start.language = new_lang
            update_wizard.do_update(update_wizard.update.get_action())

            # check the count now
            count_after = IRTranslation.search([], count=True)
            self.assertEqual(count_after, count_before * 2)

    def test_0400_translation_export(self):
        """
        Export the translations and test
        """
        TranslationSet = POOL.get('ir.translation.set', type='wizard')
        TranslationUpdate = POOL.get('ir.translation.update', type='wizard')
        IRTranslation = POOL.get('ir.translation')
        IRLanguage = POOL.get('ir.lang')

        with Transaction().start(DB_NAME, USER, CONTEXT):
            # First create all the translations
            session_id, _, _ = TranslationSet.create()
            set_wizard = TranslationSet(session_id)
            set_wizard.transition_set_()

            # set an additional language as translatable
            new_lang, = IRLanguage.search([
                ('translatable', '=', False)
            ], limit=1)
            new_lang.translatable = True
            new_lang.save()

            # Now update the translations
            session_id, _, _ = TranslationUpdate.create()
            update_wizard = TranslationUpdate(session_id)

            update_wizard.start.language = new_lang
            update_wizard.do_update(update_wizard.update.get_action())

            # TODO: Check the contents of the po file
            IRTranslation.translation_export(new_lang.code, 'nereid_test')
            IRTranslation.translation_export(new_lang.code, 'nereid')


def suite():
    "Nereid test suite"
    test_suite = unittest.TestSuite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestTranslation)
    )
    return test_suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
