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
from nereid import request


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

    def __init__(self, *args, **kwargs):
        self.readonly = kwargs.pop('readonly', None)
        self.is_csrf_exempt = kwargs.pop('exempt_csrf', False)
        super(Rule, self).__init__(*args, **kwargs)

    def empty(self):
        """Return an unbound copy of this rule.  This can be useful if you
        want to reuse an already bound URL for another map.

        Ref: https://github.com/mitsuhiko/werkzeug/pull/645
        """
        defaults = None
        if self.defaults:
            defaults = dict(self.defaults)
        return self.__class__(
            self.rule, defaults, self.subdomain, self.methods,
            self.build_only, self.endpoint, self.strict_slashes,
            self.redirect_to, self.alias, self.host
        )

    @property
    def is_readonly(self):
        if self.readonly is not None:
            # If a value that is not None is explicitly set for the URL,
            # then return that.
            return self.readonly
        # By default GET and HEAD requests are allocated a readonly cursor
        return request.method in ('HEAD', 'GET')
