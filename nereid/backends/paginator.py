# -*- coding: UTF-8 -*-
'''
    nereid.backend.paginator

    General Pagination

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
from __future__ import absolute_import

from ..exceptions import NotImplementedYet


class Pagination(object):
    """
    General purpose paginator for doing pagination
    """

    def __init__(self, klass, domain, per_page, page, order):
        """
        :param klass: The object itself. pass self within tryton object
        :param domain: Domain for search in tryton
        :param per_page: Items per page
        :param page: The page to be displayed
        """
        self.klass = klass
        self.domain = domain
        self.per_page = per_page
        self.page = page
        self.order = order

    @property
    def count(self):
        """
        Returns the count of entries
        """
        raise NotImplementedYet()

    @property
    def entries(self):
        """
        Returns the list of browse records
        """
        raise NotImplementedYet

    offset = property(lambda x: (x.page - 1) * x.per_page)

    has_previous = property(lambda x: x.page > 1)
    has_next = property(lambda x: x.page < x.pages)
    previous = property(lambda x: url_for(x.endpoint, page=x.page - 1))
    next = property(lambda x: url_for(x.endpoint, page=x.page + 1))
    pages = property(lambda x: max(0, x.count - 1) // x.per_page + 1)

