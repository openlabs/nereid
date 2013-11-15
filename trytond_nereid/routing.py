# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import pytz
from werkzeug import abort, redirect
from wtforms import Form, TextField, PasswordField, validators

from nereid import jsonify, flash, render_template, url_for, cache
from nereid.globals import session, request
from nereid.helpers import login_required, key_from_list, get_flashed_messages
from nereid.signals import login, failed_login, logout
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool

from .i18n import _

__all__ = ['URLMap', 'WebSite', 'WebSiteLocale', 'URLRule', 'URLRuleDefaults',
           'WebsiteCountry', 'WebsiteCurrency', 'WebsiteWebsiteLocale']


class URLMap(ModelSQL, ModelView):
    """
    URL Map
    ~~~~~~~

    A collection of URLs for a website. This is analogous to werkzeug's
    URL Map.

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
        return rule_args


class LoginForm(Form):
    "Default Login Form"
    email = TextField(_('e-mail'), [validators.Required(), validators.Email()])
    password = PasswordField(_('Password'), [validators.Required()])


class WebSite(ModelSQL, ModelView):
    """
    One of the most powerful features of Nereid is the ability to
    manage multiple websites from one back-end. A web site in nereid
    represents a collection or URLs, settings.

    :param name: Name of the web site
    :param base_url: The unique URL of the website, You cannot have two
                     websites, with the same base_url
    :param url_map: The active URL Map for the website (M2O URLMap)
    :param company: The company linked with the website.
    :param active: Whether the website is active or not.

    """
    __name__ = "nereid.website"

    #: The name field is used for both information and also as
    #: the site identifier for nereid. The WSGI application requires
    #: SITE argument. The SITE argument is then used to load URLs and
    #: other settings for the website. Needs to be unique
    name = fields.Char('Name', required=True, select=True)

    #: The URLMap is made as a different object which functions as a
    #: collection of Rules. This will allow easy replication of sites
    #: which perform with same URL structures but different templates
    url_map = fields.Many2One('nereid.url_map', 'URL Map', required=True)

    #: The company to which the website belongs. Useful when creating
    #: records like sale order which require a company to be present
    company = fields.Many2One('company.company', 'Company', required=True)

    active = fields.Boolean('Active')

    #: The list of countries this website operates in. Used for generating
    #: Countries list in the registration form etc.
    countries = fields.Many2Many(
        'nereid.website-country.country', 'website', 'country',
        'Countries Available')

    #: Allowed currencies in the website
    currencies = fields.Many2Many(
        'nereid.website-currency.currency',
        'website', 'currency', 'Currencies Available')

    #: Default locale
    default_locale = fields.Many2One(
        'nereid.website.locale', 'Default Locale',
        required=True
    )

    #: Allowed locales in the website
    locales = fields.Many2Many(
        'nereid.website-nereid.website.locale',
        'website', 'locale', 'Languages Available')

    #: The res.user with which the nereid application will be loaded
    #:  .. versionadded: 0.3
    application_user = fields.Many2One(
        'res.user', 'Application User', required=True
    )
    guest_user = fields.Many2One(
        'nereid.user', 'Guest user', required=True
    )

    timezone = fields.Selection(
        [(x, x) for x in pytz.common_timezones], 'Timezone', translate=False
    )

    @staticmethod
    def default_timezone():
        return 'UTC'

    @staticmethod
    def default_active():
        return True

    @classmethod
    def __setup__(cls):
        super(WebSite, cls).__setup__()
        cls._sql_constraints = [
            ('name_uniq', 'UNIQUE(name)',
             'Another site with the same name already exists!')
        ]

    @classmethod
    def country_list(cls):
        """
        Return the list of countries in JSON
        """
        return jsonify(result=[
            {'key': c.id, 'value': c.name}
            for c in request.nereid_website.countries
        ])

    @staticmethod
    def subdivision_list():
        """
        Return the list of states for given country
        """
        country = int(request.args.get('country', 0))
        if country not in [c.id for c in request.nereid_website.countries]:
            abort(404)

        Subdivision = Pool().get('country.subdivision')
        subdivisions = Subdivision.search([('country', '=', country)])
        return jsonify(
            result=[{
                'id': s.id,
                'name': s.name,
                'code': s.code,
            } for s in subdivisions
            ]
        )

    def get_urls(self, name):
        """
        Return complete list of URLs
        """
        URLMap = Pool().get('nereid.url_map')
        websites = self.search([('name', '=', name)])
        if not websites:
            raise RuntimeError("Website with Name %s not found" % name)

        return URLMap.get_rules_arguments(websites[0].url_map.id)

    def stats(self, **arguments):
        """
        Test method.
        """
        return u'Request: %s\nArguments: %s\nEnviron: %s\n' \
            % (request, arguments, request.environ)

    @classmethod
    def home(cls):
        "A dummy home method which just renders home.jinja"
        return render_template('home.jinja')

    @classmethod
    def login(cls):
        """
        Simple login based on the email and password

        Required post data see :class:LoginForm
        """
        login_form = LoginForm(request.form)

        if not request.is_guest_user and request.args.get('next'):
            return redirect(request.args['next'])

        if request.method == 'POST' and login_form.validate():
            NereidUser = Pool().get('nereid.user')
            result = NereidUser.authenticate(
                login_form.email.data, login_form.password.data
            )
            # Result can be the following:
            # 1 - Browse record of User (successful login)
            # 2 - None - Login failure without message
            # 3 - Any other false value (no message is shown. useful if you
            #       want to handle the message shown to user)
            if result:
                # NOTE: Translators leave %s as such
                flash(_("You are now logged in. Welcome %(name)s",
                        name=result.display_name))
                session['user'] = result.id
                login.send()
                if request.is_xhr:
                    return 'OK'
                else:
                    return redirect(
                        request.values.get(
                            'next', url_for('nereid.website.home')
                        )
                    )
            elif result is None:
                flash(_("Invalid login credentials"))

            failed_login.send(form=login_form)

            if request.is_xhr:
                return 'NOK'

        return render_template('login.jinja', login_form=login_form)

    @classmethod
    def logout(cls):
        "Log the user out"
        session.pop('user', None)
        logout.send()
        flash(
            _('You have been logged out successfully. Thanks for visiting us')
        )
        return redirect(
            request.args.get('next', url_for('nereid.website.home'))
        )

    @staticmethod
    def account_context():
        """This fills the account context for the template
        rendering my account. Additional modules might want to fill extra
        data into the context
        """
        return dict(
            user=request.nereid_user,
            party=request.nereid_user.party,
        )

    @classmethod
    @login_required
    def account(cls):
        return render_template('account.jinja', **cls.account_context())

    def get_currencies(self):
        """Returns available currencies for current site

        .. note::
            A special method is required so that the fetch can be speeded up,
            by pushing the categories to the central cache which cannot be
            done directly on a browse node.
        """
        cache_key = key_from_list([
            Transaction().cursor.dbname,
            Transaction().user,
            'nereid.website.get_currencies',
        ])
        # The website is automatically appended to the cache prefix
        rv = cache.get(cache_key)
        if rv is None:
            rv = [{
                'id': c.id,
                'name': c.name,
                'symbol': c.symbol,
            } for c in self.currencies
            ]
            cache.set(cache_key, rv, 60 * 60)
        return rv

    @staticmethod
    def _user_status():
        """Returns the commonly required status parameters of the user

        This method could be inherited and components could be added
        """
        rv = {
            'messages': get_flashed_messages()
        }
        if request.is_guest_user:
            rv.update({
                'logged_id': False
            })
        else:
            rv.update({
                'logged_in': True,
                'name': request.nereid_user.display_name
            })
        return rv

    @classmethod
    def user_status(cls):
        """
        Returns a JSON of the user_status
        """
        return jsonify(status=cls._user_status())


class WebSiteLocale(ModelSQL, ModelView):
    'Web Site Locale'
    __name__ = "nereid.website.locale"
    _rec_name = 'code'

    code = fields.Char('Code', required=True)
    language = fields.Many2One(
        'ir.lang', 'Default Language', required=True
    )
    currency = fields.Many2One(
        'currency.currency', 'Currency', ondelete='CASCADE', required=True
    )

    @classmethod
    def __setup__(cls):
        super(WebSiteLocale, cls).__setup__()
        cls._sql_constraints += [
            ('unique_code', 'UNIQUE(code)',
                'Code must be unique'),
        ]


class URLRule(ModelSQL, ModelView):
    """
    URL Rule
    ~~~~~~~~

    A rule that represents a single URL pattern

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

        .. versionadded: 2.4.0.6
        """
        methods = []
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


class WebsiteCountry(ModelSQL):
    "Website Country Relations"
    __name__ = 'nereid.website-country.country'

    website = fields.Many2One('nereid.website', 'Website')
    country = fields.Many2One('country.country', 'Country')


class WebsiteCurrency(ModelSQL):
    "Currencies to be made available on website"
    __name__ = 'nereid.website-currency.currency'
    _table = 'website_currency_rel'

    website = fields.Many2One(
        'nereid.website', 'Website',
        ondelete='CASCADE', select=1, required=True)
    currency = fields.Many2One(
        'currency.currency', 'Currency',
        ondelete='CASCADE', select=1, required=True)


class WebsiteWebsiteLocale(ModelSQL):
    "Languages to be made available on website"
    __name__ = 'nereid.website-nereid.website.locale'
    _table = 'website_locale_rel'

    website = fields.Many2One(
        'nereid.website', 'Website',
        ondelete='CASCADE', select=1, required=True)
    locale = fields.Many2One(
        'nereid.website.locale', 'Locale',
        ondelete='CASCADE', select=1, required=True)
