# -*- coding: utf-8 -*-
"""
    The host matching URL Map seems to be matching hosts well but fails in
    generating/building URLs when there are same endpoints.

    This patch makes strict host matching to ensure nothing skips host
    matching.

    Also see: https://github.com/mitsuhiko/werkzeug/issues/488

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from werkzeug import routing


class Map(routing.Map):
    def _partial_build(self, endpoint, values, method, append_unknown):
        """Helper for :meth:`build`.  Returns subdomain and path for the
        rule that accepts this endpoint, values and method.

        :internal:
        """
        # in case the method is none, try with the default method first
        if method is None:
            rv = self._partial_build(endpoint, values, self.default_method,
                                     append_unknown)
            if rv is not None:
                return rv

        host = self.map.host_matching and self.server_name or self.subdomain

        # default method did not match or a specific method is passed,
        # check all and go with first result.
        for rule in self.map._rules_by_endpoint.get(endpoint, ()):
            if rule.suitable_for(values, method, host):
                rv = rule.build(values, append_unknown)
                if rv is not None:
                    return rv


class Rule(routing.Rule):

    def suitable_for(self, values, method=None, host=None):
        """Check if the dict of values has enough data for url generation.

        :internal:
        """
        rv = super(Rule, self).build(values, method)

        # if host matching is enabled and the hosts dont match, then
        # this is not a suitable match
        if rv and self.map and self.map.host_matching and self.host != host:
            return False

        return rv
