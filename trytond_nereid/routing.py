# -*- coding: UTF-8 -*-
"""
    nereid.routing

    Routing: Sites, URLs

    :copyright: (c) 2010 by Sharoon Thomas
    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
"""
from ast import literal_eval

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

# pylint: disable-msg=E1101
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
    _name = "nereid.url_map"
    _description = "Nereid URL Map"

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

    def default_active(self):
        "By default URL is active"
        return True

    def default_charset(self):
        "By default characterset is utf-8"
        return 'utf-8'

    def get_rules_arguments(self, map_id):
        """
        Constructs a list of dictionary of arguments needed
        for URL Rule construction. A wrapper around the 
            URL RULE get_rule_arguments
        """
        rule_args = [ ]
        rule_obj = Pool().get('nereid.url_rule')
        url_map = self.browse(map_id)
        for rule in url_map.rules:
            rule_args.append(
                rule_obj.get_rule_arguments(rule.id)
            )
        return rule_args

URLMap()


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
    _name = "nereid.website"
    _description = "Nereid WebSite"

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

    #: Default language
    default_language = fields.Many2One('ir.lang', 'Default Language',
        required=True)

    #: The res.user with which the nereid application will be loaded
    #:  .. versionadded: 0.3
    application_user = fields.Many2One(
        'res.user', 'Application User', required=True
    )
    guest_user = fields.Many2One(
        'nereid.user', 'Guest user', required=True
    )

    def default_active(self):
        return True

    def __init__(self):
        super(WebSite, self).__init__()
        self._sql_constraints = [
            ('name_uniq', 'UNIQUE(name)',
             'Another site with the same name already exists!')
        ]

    def country_list(self):
        """
        Return the list of countries in JSON
        """
        return jsonify(result = [
            {'key': c.id, 'value': c.name} \
                for c in request.nereid_website.countries
            ])

    def subdivision_list(self):
        """
        Return the list of states for given country
        """
        country = int(request.args.get('country', 0))
        if country not in [c.id for c in request.nereid_website.countries]:
            abort(404)

        subdivision_obj = Pool().get('country.subdivision')
        ids = subdivision_obj.search([('country', '=', country)])
        subdivisions = subdivision_obj.browse(ids)
        return jsonify(
            result = [{
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
        url_map_obj = Pool().get('nereid.url_map')
        website_id = self.search([('name', '=', name)])
        if not website_id:
            raise RuntimeError("Website with Name %s not found" % name)

        website = self.browse(website_id[0])
        return url_map_obj.get_rules_arguments(website.url_map.id)

    def stats(self, **arguments):
        """
        Test method.
        """
        return u'Request: %s\nArguments: %s\nEnviron: %s\n' \
            % (request, arguments, request.environ)

    def home(self):
        "A dummy home method which just renders home.jinja"
        return render_template('home.jinja')

    def login(self):
        """
        Simple login based on the email and password

        Required post data see :class:LoginForm
        """
        login_form = LoginForm(request.form)

        if not request.is_guest_user and request.args.get('next'):
            return redirect(request.args['next'])

        if request.method == 'POST' and login_form.validate():
            user_obj = Pool().get('nereid.user')
            result = user_obj.authenticate(
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
                    name=result.name))
                session['user'] = result.id
                login.send(self)
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

            failed_login.send(self, form=login_form)

            if request.is_xhr:
                return 'NOK'

        return render_template('login.jinja', login_form=login_form)

    def logout(self):
        "Log the user out"
        session.pop('user', None)
        logout.send(self)
        flash(
            _('You have been logged out successfully. Thanks for visiting us')
        )
        return redirect(
            request.args.get('next', 
            url_for('nereid.website.home'))
        )

    def account_context(self):
        """This fills the account context for the template
        rendering my account. Additional modules might want to fill extra 
        data into the context
        """
        return dict(
            user = request.nereid_user,
            party = request.nereid_user.party,
        )

    @login_required
    def account(self):
        context = self.account_context()
        return render_template('account.jinja', **context)

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
                } for c in request.nereid_website.currencies]
            cache.set(cache_key, rv, 60*60)
        return rv

    def set_currency(self):
        """Set the currency for the current session.

        Accepted Methods: GET, POST
        Accepts XHR: Yes
        """
        currency = int(request.values.get('currency', 0))
        if currency not in [c['id'] for c in self.get_currencies()]:
            abort(403)  # Forbidden currency

        session['currency'] = currency
        message = _("The currency has been successfully changed")

        if request.is_xhr:
            return jsonify(result = {'success': True, 'message': message})

        flash(message)
        # redirect to the next url if given else take to home page
        return redirect(
            request.values.get('next', url_for('nereid.website.home'))
            )

    def get_languages(self):
        """Returns available languages for current site

        .. note:: 
            A special method is required so that the fetch
            can be speeded up, by pushing the categories to the central cache
            which cannot be done directly on a browse node.
        """
        lang_obj = Pool().get('ir.lang')

        cache_key = key_from_list([
            Transaction().cursor.dbname,
            Transaction().user,
            'nereid.website.get_languages',
            ])
        # The website is automatically appended to the cache prefix
        rv = cache.get(cache_key)
        if rv is None:
            language_ids = lang_obj.search([('translatable', '=', True)])
            languages = lang_obj.browse(language_ids)
            rv = [{
                'id': l.id,
                'name': l.name,
                'code': l.code,
                } for l in languages]
            cache.set(cache_key, rv, 60*60)
        return rv

    def set_language(self):
        """Sets the language in the session of the user. Also try to guess the
        currency of the user, if not use the default currency of the website

        Accepted Methods: GET, POST
        Accepts XHR: Yes

        The language has to be provided in the GET arguments of POST form. It 
        is more convenient to pass the language code than the id of the 
        language because it makes it more readable in URLs
        """
        raise DeprecationWarning("Set language is deprecated")
        lang_obj = Pool().get('ir.lang')

        language = request.values.get('language')
        exists = lang_obj.search([('code', '=', language)], limit=1)

        if exists:
            flash(_('Your language preference have been saved.'))
        else:
            flash(_('Sorry! we do not speak your language yet!'))

        # redirect to the next url if given else take to home page
        redirect_to = request.values.get('next')
        if redirect_to:
            redirect_to.replace(session['language'], language)
        return redirect(
            request.values.get('next', url_for('nereid.website.home'))
            )

    def _user_status(self):
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
                'name': request.nereid_user.name
                })
        return rv

    def user_status(self):
        """
        Returns a JSON of the user_status
        """
        return jsonify(status=self._user_status())

WebSite()


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
    _name = "nereid.url_rule"
    _description = "Nereid URL Rule"
    _rec_name = 'rule'

    rule = fields.Char('Rule', required=True, select=True,)
    endpoint = fields.Char('Endpoint', select=True,)
    active = fields.Boolean('Active')
    defaults = fields.One2Many('nereid.url_rule_defaults', 'rule', 'Defaults')
    methods = fields.Selection(
        [
            ('("POST",)', 'POST'),
            ('("GET",)', 'GET'),
            ('("GET", "POST")', 'GET/POST')
        ],
        'Methods', required=True)
    only_for_genaration = fields.Boolean('Only for Generation')
    redirect_to = fields.Char('Redirect To')
    sequence = fields.Integer('Sequence', required=True,)
    url_map = fields.Many2One('nereid.url_map', 'URL Map')

    def __init__(self):
        super(URLRule, self).__init__()
        self._order.insert(0, ('sequence', 'ASC'))

    def default_active(self):
        return True

    def default_methods(self):
        return '("GET",)'

    def get_rule_arguments(self, rule_id):
        """
        Return the arguments of a Rule in the corresponding format
        """
        rule = self.browse(rule_id)
        defaults = dict(
            [(i.key, i.value) for i in rule.defaults]
        )
        return {
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': rule.methods and literal_eval(rule.methods) or None,
                'build_only': rule.only_for_genaration,
                'defaults': defaults,
                'redirect_to': rule.redirect_to or None,
            }

URLRule()


class URLRuleDefaults(ModelSQL, ModelView):
    """
    Defaults for the URL

    :param key: The char for the default's key
    :param value: The Value for the default's Value
    :param Rule: M2O Rule
    """
    _name = "nereid.url_rule_defaults"
    _description = "Nereid URL Rule Defaults"
    _rec_name = 'key'

    key = fields.Char('Key', required=True, select=True)
    value = fields.Char('Value', required=True, select=True)
    rule = fields.Many2One('nereid.url_rule', 'Rule', required=True, 
        select=True)

URLRuleDefaults()


class WebsiteCountry(ModelSQL):
    "Website Country Relations"
    _name = 'nereid.website-country.country'
    _description = __doc__

    website = fields.Many2One('nereid.website', 'Website')
    country = fields.Many2One('country.country', 'Country')

WebsiteCountry()


class WebsiteCurrency(ModelSQL):
    "Currencies to be made available on website"
    _name = 'nereid.website-currency.currency'
    _table = 'website_currency_rel'
    _description = __doc__

    website = fields.Many2One(
        'nereid.website', 'Website', 
        ondelete='CASCADE', select=1, required=True)
    currency = fields.Many2One(
        'currency.currency', 'Currency', 
        ondelete='CASCADE', select=1, required=True)

WebsiteCurrency()
