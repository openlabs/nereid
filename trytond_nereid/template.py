# -*- coding: UTF-8 -*-
"""
    nereid_configuration.template

    Template Management

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd
    :copyright: (c) 2010 by Sharoon Thomas
    :license: GPLv3, see LICENSE for more details
"""
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool


class Template(ModelSQL, ModelView):
    """
    Templates

    `name`: Name of template
    `source`: Source of the template, This should probably be a text field
    `language`: Selection of Language

    The name, language pair has to be unique.

    .. tip::
        The database based template loading is far from appropriate for
        a production setup. This is mostly used in testing.
    """
    _name = "nereid.template"
    _description = "Nereid Template"

    name = fields.Char('Name', required=True, select=True)
    source = fields.Text('Source', required=True)
    language = fields.Many2One('ir.lang', 'Language', required=True)
    website = fields.Many2One('nereid.website', 'Website')

    def __init__(self):
        super(Template, self).__init__()
        self._sql_constraints = [
            ('name_lang_site_uniq', 'UNIQUE(name, language, website)',
             'Another template with same name'
             ' and language already exists in the website!')
        ]

    def get_template_source(self, name):
        """
        Wraps _get_template_source for efficient caching
        """
        website_obj = Pool().get('nereid.website')

        # Nereid tries to load template from different websites by passing
        # the name of template like <website>/<template>.
        website_name, template = name.split('/', 1)
        website_id, = website_obj.search([('name', '=', website_name)])

        return self._get_template_source(
            template, website_id,
            Transaction().context.get('language', 'en_US')
        )

    def _get_template_source(self, name, website, lang):
        """
        Returns the source of the template requested

        If not found it returns None
        """
        lang_obj = Pool().get('ir.lang')
        lang_id, = lang_obj.search([('code', '=', lang)])

        # Search with full spec
        template_ids = self.search([
            ('name', '=', name), 
            ('language', '=', lang_id), 
            ('website', '=', website)])

        # Search with website param relaxed
        if not template_ids:
            template_ids = self.search([
                ('name', '=', name), 
                ('language', '=', lang_id), 
                ('website', '=', False)
                ])

        # Search with english as language for specific website
        if not template_ids:
            template_ids = self.search([
                ('name', '=', name), 
                ('language.code', '=', 'en_US'), 
                ('website', '=', website)])

        # Search with english as language for relaxed website param
        if not template_ids:
            template_ids = self.search([
                ('name', '=', name), 
                ('language.code', '=', 'en_US'), 
                ('website', '=', False)])

        if not template_ids:
            return None

        template, = self.browse(template_ids)
        return template.source

Template()


class ContextProcessors(ModelSQL, ModelView):
    "Temlate Context Processor Registry"
    _name = 'nereid.template.context_processor'
    _description = __doc__
    _rec_name = 'function'

    method = fields.Char('Method', required=True, 
        help="Context processor method in <model>.<method>")
    model = fields.Char('Model', 
        help="This will restrict the loading when URLs with"
        " the model are called")

    def get_processors(self):
        """Return the list of processors. Separate function
        since its important to have caching on this
        """
        result = { }
        ids = self.search([])
        for ctx_proc in self.browse(ids):
            model, method = ctx_proc.method.rsplit('.', 1)
            ctx_proc_as_func = getattr(Pool().get(model), method)
            result.setdefault(ctx_proc.model or None, []).append(
                ctx_proc_as_func)
        return result

ContextProcessors()
