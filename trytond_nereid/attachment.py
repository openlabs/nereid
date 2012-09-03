# -*- coding: utf-8 -*-
"""
    ir_attachment

    Attachment

    :copyright: © 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from nereid import request
from nereid.ctx import has_request_context
from trytond.model import ModelView, ModelSQL, fields


class IrAttachment(ModelSQL, ModelView):
    "Ir Attachment"
    _name = 'ir.attachment'

    uploaded_by = fields.Many2One('nereid.user', 'Uploaded By')

    def create(self, values):
        """
        Update create to save uploaded by

        :param values: A dictionary
        """
        if has_request_context():
            values['uploaded_by'] = request.nereid_user.id
        #else:
            # TODO: try to find the nereid user from the employee
            # if an employee made the update

        return super(IrAttachment, self).create(values)

IrAttachment()
