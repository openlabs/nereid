# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView
from trytond.wizard import Wizard, StateView, Button, StateTransition
from trytond.pool import PoolMeta

__all__ = ['NereidConfigStart', 'NereidConfig']
__metaclass__ = PoolMeta


class NereidConfigStart(ModelView):
    'Nereid Config'
    __name__ = 'nereid.website.config.start'


class NereidConfig(Wizard):
    'Configure Nereid'
    __name__ = 'nereid.website.config'
    start = StateView(
        'nereid.website.config.start',
        'nereid.website_config_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'website', 'tryton-ok', True),
        ]
    )
    website = StateView(
        'nereid.website',
        'nereid.website_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', True),
        ]
    )
    add = StateTransition()

    def transition_add(self):
        """
        Add website during transition and close the wizard.
        """
        self.website.save()
        return 'end'
