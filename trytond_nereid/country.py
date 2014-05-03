# -*- coding: utf-8 -*-
"""
    Country

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta, Pool
from nereid import jsonify, route

__metaclass__ = PoolMeta

__all__ = ['Country', 'Subdivision']


class Country:
    "Country"

    __name__ = 'country.country'

    @classmethod
    @route("/all-countries", methods=["GET"])
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

    @route("/countries/<int:active_id>/subdivisions", methods=["GET"])
    def get_subdivisions(self):
        """
        Returns serialized list of all subdivisions for current country
        """
        Subdivision = Pool().get('country.subdivision')

        subdivisions = Subdivision.search([('country', '=', self.id)])
        return jsonify(
            result=[s.serialize() for s in subdivisions]
        )


class Subdivision:
    "Subdivision"

    __name__ = 'country.subdivision'

    def serialize(self, purpose=None):
        """
        Serialize subdivision data
        """
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
        }
