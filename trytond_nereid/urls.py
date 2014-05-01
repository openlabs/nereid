# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import warnings

from trytond.model import ModelView, ModelSQL, fields

__all__ = ['URLMap', 'URLRule', 'URLRuleDefaults']


class URLMap(ModelSQL, ModelView):
    """
    URL Map
    ~~~~~~~

    A collection of URLs for a website. This is analogous to werkzeug's
    URL Map.

    .. warning::

        Defining URLs int he database (using XML) will be deprecated in 3.2.1.0
        Use the `route` decorator to route instead.

        See: https://github.com/openlabs/nereid/issues/178

    :param name: Name of the URL Map
    :param default_subdomain: Default subdomain for URLs in this Map
    :param active: Whether the URL Map is active or not.

    Rules:
    ~~~~~~
    :param rules: O2M URLRules

    Advanced:
    ~~~~~~~~~
    :param charset: default value - utf-8
    :param strict_slashes: Boolean field if / in url map is taken seriously
    :param unique_urls: Enable `redirect_defaults` in the URL Map and
                        redirects the defaults to the URL
    """
    __name__ = "nereid.url_map"

    name = fields.Char(
        'Name', required=True, select=True,
    )
    default_subdomain = fields.Char(
        'Default Subdomain',
    )
    rules = fields.One2Many(
        'nereid.url_rule',
        'url_map',
        'Rules'
    )
    charset = fields.Char('Char Set')
    strict_slashes = fields.Boolean('Strict Slashes')
    unique_urls = fields.Boolean('Unique URLs')
    active = fields.Boolean('Active')

    @staticmethod
    def default_active():
        "By default URL is active"
        return True

    @staticmethod
    def default_charset():
        "By default characterset is utf-8"
        return 'utf-8'

    def get_rules_arguments(self):
        """
        Constructs a list of dictionary of arguments needed
        for URL Rule construction. A wrapper around the
            URL RULE get_rule_arguments
        """
        rule_args = []
        for rule in self.rules:
            rule_args.append(rule.get_rule_arguments())

        if rule_args:
            warnings.warn(
                "Use of XML/Database to bind URLs to view function will be "
                "deprecated in version 3.2.1.0.\n\n"
                "Use the route decorator instead.\n\n"
                "See: https://github.com/openlabs/nereid/issues/178",
                DeprecationWarning
            )

        return rule_args


class URLRule(ModelSQL, ModelView):
    """
    URL Rule
    ~~~~~~~~

    A rule that represents a single URL pattern

    .. warning::

        Defining URLs int he database (using XML) will be deprecated in 3.2.1.0.
        Use the `route` decorator to route instead.

        See: https://github.com/openlabs/nereid/issues/178

    :param path: Path of the URL
    :param name: Name of the URL. This is used for reverse mapping, hence
                 needs to be unique
    :param handler: The handler of this URL or the target model.method
                     which is called. The representation is::

        <model>.<method>

    For example: To call list_parties method in party.party use:

        party.party.list_parties

    The signature of the method being called should be:

        def method(self, **arguments):
            return "Hello World"

    where request is the request object and arguments is the dictionary
    of the values generated from the match of the URL

    :param active: Whether the website is active or not.

    Advanced
    ~~~~~~~~~

    :param defaults: Defaults of the URL (O2M - URLRuleDefaults)

    :param method: POST, GET,
    :param only_for_generation: URL will not be mapped, but can be used
            for URL generation. Example for static pages, where content
            delivery is managed by apache, but URL generation is necessary
    :param redirect_to: (M2O self) Another URL to which the redirect has to
            be done
    :param sequence: Numeric sequence of the URL Map.
    :param url_map: Relation field for url_rule o2m
    """
    __name__ = "nereid.url_rule"
    _rec_name = 'rule'

    rule = fields.Char('Rule', required=True, select=True,)
    endpoint = fields.Char('Endpoint', select=True,)
    active = fields.Boolean('Active')
    defaults = fields.One2Many('nereid.url_rule_defaults', 'rule', 'Defaults')

    # Supported HTTP methods
    http_method_get = fields.Boolean('GET')
    http_method_post = fields.Boolean('POST')
    http_method_patch = fields.Boolean('PATCH')
    http_method_put = fields.Boolean('PUT')
    http_method_delete = fields.Boolean('DELETE')

    only_for_genaration = fields.Boolean('Only for Generation')
    redirect_to = fields.Char('Redirect To')
    sequence = fields.Integer('Sequence', required=True,)
    url_map = fields.Many2One('nereid.url_map', 'URL Map')

    @classmethod
    def __setup__(cls):
        super(URLRule, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_http_method_get():
        return True

    def get_http_methods(self):
        """
        Returns an iterable of HTTP methods that the URL has to support.

        .. versionchanged: 3.0.4.0

            OPTIONS is not implicitly added

        .. versionadded: 2.4.0.6
        """
        methods = ['OPTIONS']
        if self.http_method_get:
            methods.append('GET')
        if self.http_method_post:
            methods.append('POST')
        if self.http_method_put:
            methods.append('PUT')
        if self.http_method_delete:
            methods.append('DELETE')
        if self.http_method_patch:
            methods.append('PATCH')
        return methods

    def get_rule_arguments(self):
        """
        Return the arguments of a Rule in the corresponding format
        """
        defaults = dict(
            [(i.key, i.value) for i in self.defaults]
        )
        return {
            'rule': self.rule,
            'endpoint': self.endpoint,
            'methods': self.get_http_methods(),
            'build_only': self.only_for_genaration,
            'defaults': defaults,
            'redirect_to': self.redirect_to or None,
        }


class URLRuleDefaults(ModelSQL, ModelView):
    """
    Defaults for the URL

    .. warning::

        Defining URLs int he database (using XML) will be deprecated in 3.2.1.0.
        Use the `route` decorator to route instead.

        See: https://github.com/openlabs/nereid/issues/178

    :param key: The char for the default's key
    :param value: The Value for the default's Value
    :param Rule: M2O Rule
    """
    __name__ = "nereid.url_rule_defaults"
    _rec_name = 'key'

    key = fields.Char('Key', required=True, select=True)
    value = fields.Char('Value', required=True, select=True)
    rule = fields.Many2One(
        'nereid.url_rule', 'Rule', required=True,
        select=True
    )
