# -*- coding: utf-8 -*-
"""
    pagination

    Pagination when using sphinx search 

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
from werkzeug.utils import cached_property
from nereid.contrib.pagination import BasePagination
from .sphinxapi import SphinxClient


class SphinxPagination(BasePagination):
    """An implementation of Pagination to be used along with Sphinx Search

    If you need to specify customer filters or range filters you can set that
    on the sphinx_client attribute, which is an instance of SphinxClient. This
    could be done anywhere before rendering or further use of the pagination
    object as the query itself is lazy loaded on first access.

    Example::

        products = SphinxPagination(query, search_index, page, per_page)
        products.sphinx_client.SetFilter("warranty", [1, 2])

    The actual query is only executed when the items are fetched or pagination
    items are called.
    """

    def __init__(self, obj, query, search_index, page, per_page):
        """
        :param obj: The object itself. pass self within tryton object
        :param query: The Query text for pagination
        :param search_index: The search indices in which to look for
        :param page: The current page being displayed
        :param per_page: The number of items per page
        """
        from trytond.config import CONFIG
        if not self.sphinx_enabled():
            raise RuntimeError("Sphinx is not available or configured")

        self.obj = obj
        self.query = query
        self.search_index = search_index
        self.sphinx_client = SphinxClient()
        self.sphinx_client.SetServer(
            CONFIG.options['sphinx_server'], int(CONFIG.options['sphinx_port'])
            )
        super(SphinxPagination, self).__init__(page, per_page)

    def sphinx_enabled(self):
        """A helper method to check if the sphinx client is enabled and
        configured
        """
        from trytond.config import CONFIG
        return 'sphinx_server' in CONFIG.options and \
            'sphinx_port' in CONFIG.options

    @cached_property
    def count(self):
        "Returns the count of the items"
        return self.result['total_found']

    @cached_property
    def result(self):
        """queries the server and fetches the result. This would only be
        executed once as this is decorated as a cached property
        """
        # Note: This makes setting limits on the sphinx client basically 
        # useless as it would anyway be set using page and offset just before
        # the query is run
        self.sphinx_client.SetLimits(self.offset, self.per_page)
        rv = self.sphinx_client.Query(self.query, self.search_index)
        if rv is None:
            raise Exception(self.sphinx_client.GetLastError())
        return rv

    def all_items(self):
        """Returns all items. Sphinx by default has a limit of 1000 items
        """
        self.sphinx_client.SetLimit(0, 1000)
        return self.sphinx_client.Query(self.query, self.search_index)

    def items(self):
        """Returns the BrowseRecord of items in the current page"""
        return self.obj.browse(
            [record['id'] for record in self.result['matches']])
