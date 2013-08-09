# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool

__all__ = ['ContextProcessors']


class ContextProcessors(ModelSQL, ModelView):
    "Temlate Context Processor Registry"
    __name__ = 'nereid.template.context_processor'
    _rec_name = 'method'

    method = fields.Char(
        'Method', required=True,
        help="Context processor method in <model>.<method>"
    )
    model = fields.Char(
        'Model',
        help="This will restrict the loading when URLs with"
        " the model are called"
    )

    @classmethod
    def get_processors(cls):
        """
        Return the list of processors. Separate function
        since its important to have caching on this
        """
        result = {}
        ctx_processors = cls.search([])
        for ctx_proc in ctx_processors:
            model, method = ctx_proc.method.rsplit('.', 1)
            ctx_proc_as_func = getattr(Pool().get(model), method)
            result.setdefault(ctx_proc.model or None, []).append(
                ctx_proc_as_func)
        return result
