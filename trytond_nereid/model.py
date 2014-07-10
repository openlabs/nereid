# -*- coding: utf-8 -*-
"""
    Model

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta, Pool
from nereid import context_processor

__metaclass__ = PoolMeta

__all__ = ['ModelData']


class ModelData:
    __name__ = 'ir.model.data'

    @classmethod
    @context_processor('get_using_xml_id')
    def get_using_xml_id(cls, module, fs_id):
        """Returns active db record corresponding to fs_id
        """
        id_ = cls.get_id(module, fs_id)

        data, = cls.search([
            ('module', '=', module),
            ('fs_id', '=', fs_id),
        ], limit=1)

        return Pool().get(data.model)(id_)
