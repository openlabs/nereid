# -*- coding: utf-8 -*-
"""
    Model

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta, Pool

__metaclass__ = PoolMeta

__all__ = ['ModelData']


class ModelData:
    __name__ = 'ir.model.data'

    @classmethod
    def get_using_xml_id(cls, module, fs_id):
        """Returns active db record corresponding to fs_id
        """
        id_ = cls.get_id(module, fs_id)

        data, = cls.search([
            ('module', '=', module),
            ('fs_id', '=', fs_id),
        ], limit=1)

        return Pool().get(data.model)(id_)

    @classmethod
    def context_processor(cls):
        """This function will be called by nereid to update
        the template context. Must return a dictionary that the context
        will be updated with.
        """
        return {
            'get_using_xml_id': cls.get_using_xml_id,
        }
