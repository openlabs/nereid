# -*- coding: UTF-8 -*-
"""
    nereid_configuration.template

    Template Management

    :copyright: (c) 2010 by Sharoon Thomas, 
    :copyright: (c) 2010 by Openlabs Technologies & Consulting (P) Ltd
    :license: GPLv3, see LICENSE for more details
"""
from trytond.model import ModelView, ModelSQL, fields

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
    
    name = fields.Char(
        'Name',
        required=True,
        select=True,
    )
    source = fields.Text(
        'Source',
        required=True,
        select=True,
    )
    language = fields.Many2One(
        'ir.lang',
        'Language',
        required=True
    )

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
        lang_obj = self.pool.get('res.lang')
        lang_id, = lang_obj.search(
            [('code', '=', context.get('language', 'en_US'))]
            )
        template_ids = self.search(
            [('name', '=', name), ('language', '=', lang_id)]
            )
        if not template_ids:
            return None
        template = self.browse(template_ids[0])
        return template.source

Template()

