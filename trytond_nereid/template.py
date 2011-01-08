# -*- coding: UTF-8 -*-
"""
    nereid_configuration.template

    Template Management

    :copyright: (c) 2010 by Sharoon Thomas, 
    :copyright: (c) 2010 by Openlabs Technologies & Consulting (P) Ltd
    :license: GPLv3, see LICENSE for more details
"""
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction


class Template(ModelSQL, ModelView):
    """
    Templates

    `name`: Name of template
    `source`: Source of the template, This should probably be a text field
    `language`: Selection of Language

    The name, language pair has to be unique
    """
    _name = "nereid.template"
    _description = "Nereid Template"
    
    name = fields.Char('Name', required=True, select=True)
    source = fields.Text('Source', required=True, select=True)
    language = fields.Many2One('ir.lang', 'Language', required=True)

    def __init__(self):
        super(Template, self).__init__()
        self._sql_constraints = [
            ('name_lang_uniq', 'UNIQUE(name, language)',
             'Another template with same name and language already exists!')
        ]

    def get_template_source(self, name):
        """
        Returns the source of the template requested

        If not found it returns None
        """
        lang_obj = self.pool.get('ir.lang')
        lang_id, = lang_obj.search(
            [('code', '=', Transaction().context.get('language', 'en_US'))])
        template_ids = self.search(
            [('name', '=', name), ('language', '=', lang_id)])
        if not template_ids:
            return None
        template = self.browse(template_ids[0])
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
            ctx_proc_as_func = getattr(self.pool.get(model), method)
            result.setdefault(ctx_proc.model or None, []).append(
                ctx_proc_as_func)
        return result

ContextProcessors()
