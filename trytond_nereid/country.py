# -*- coding: utf-8 -*-
"""
    Country

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta
from nereid import jsonify

__metaclass__ = PoolMeta

__all__ = ['Country']


class Country:
    "Country"

    __name__ = 'country.country'

    @classmethod
    def get_all_countries(cls):
        """
        Returns serialized list of all countries
        """
        return jsonify(countries=[
            country.serialize() for country in cls.search([])
        ])

    def serialize(self, purpose=None):
        """
        Serialize country data
        """
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code
        }
