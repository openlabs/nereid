# -*- coding: UTF-8 -*-
"""

    Template Management

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd
    :copyright: (c) 2010 by Sharoon Thomas
    :license: GPLv3, see LICENSE for more details
"""
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool


class ContextProcessors(ModelSQL, ModelView):
    "Temlate Context Processor Registry"
    _name = 'nereid.template.context_processor'
    _description = __doc__
    _rec_name = 'method'

    method = fields.Char('Method', required=True, 
        help="Context processor method in <model>.<method>")
    model = fields.Char('Model', 
        help="This will restrict the loading when URLs with"
        " the model are called")

    def get_processors(self):
        """
        Return the list of processors. Separate function
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
