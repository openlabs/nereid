# -*- coding: utf-8 -*-
"""
    nereid.testing
    ~~~~~~~~~~~~~

    Implements test support helpers.  This module is lazily imported
    and usually not used in production environments.

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import new

from werkzeug import Client, EnvironBuilder
from nereid import _request_ctx_stack


class NereidClient(Client):
    """Works like a regular Werkzeug test client but has some
    knowledge about how Nereid works to defer the cleanup of the
    request context stack to the end of a with body when used
    in a with statement.
    """

    preserve_context = context_preserved = False

    def open(self, *args, **kwargs):
        if self.context_preserved:
            _request_ctx_stack.pop()
            self.context_preserved = False
        kwargs.setdefault('environ_overrides', {}) \
            ['nereid._preserve_context'] = self.preserve_context

        as_tuple = kwargs.pop('as_tuple', False)
        buffered = kwargs.pop('buffered', False)
        follow_redirects = kwargs.pop('follow_redirects', False)

        builder = EnvironBuilder(*args, **kwargs)

        if self.application.config.get('SERVER_NAME'):
            server_name = self.application.config.get('SERVER_NAME')
            if ':' not in server_name:
                http_host, http_port = server_name, None
            else:
                http_host, http_port = server_name.split(':', 1)
            if builder.base_url == 'http://localhost/':
                # Default Generated Base URL
                if http_port != None:
                    builder.host = http_host + ':' + http_port
                else:
                    builder.host = http_host
        old = _request_ctx_stack.top
        try:
            return Client.open(self, builder,
                               as_tuple=as_tuple,
                               buffered=buffered,
                               follow_redirects=follow_redirects)
        finally:
            self.context_preserved = _request_ctx_stack.top is not old

    def __enter__(self):
        self.preserve_context = True
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.preserve_context = False
        if self.context_preserved:
            _request_ctx_stack.pop()


class TestingProxy(object):
    """A collection of helper methods to make testing easier by creating
    a convenience class which could be passed around for testing methods 
    like the one documented below.
    """

    def __init__(self):
        """Required for initialisation and easy access to other members
        """
        self.initialised = False

    def init(self):
        from trytond.config import CONFIG
        CONFIG['database_type'] = 'sqlite'
        self.db_name = ':memory:'

        from trytond.backend import Database
        database = Database()
        cursor = database.cursor()
        databases = database.list(cursor)
        cursor.close()

        if self.db_name not in databases:
            from trytond.protocols.dispatcher import create
            create(self.db_name, 'admin', 'en_US', 'admin')

        from trytond.pool import Pool
        self.pool = Pool(self.db_name)
        self.pool.init()

        self.user = 1
        self.context = None

    def install_module(self, module):
        if not self.initialised:
            self.init()
        from trytond.transaction import Transaction
        with Transaction().start(self.db_name, self.user, self.context) as txn:
            module_obj = self.pool.get('ir.module.module')
            module = module_obj.search([('name', '=', module)])
            module_obj.button_install(module)

            install_wizard = self.pool.get('ir.module.module.install_upgrade', 
                type="wizard")
            wiz_id = install_wizard.create()
            install_wizard.execute(wiz_id, {}, 'start')
            txn.cursor.commit()

    def register(self, name=None):
        """A decorator that is used to register functions for being attached
        as helper method for testing

        Eg:

            @testing_proxy.regsiter()
            def create_something(obj, arg):
                pass

        """
        def decorator(f):
            method_name = f.func_name if not name else name
            setattr(self, method_name, new.instancemethod(
                f, self, TestingProxy))
            return f
        return decorator

    def make_app(self, **options):
        """Creates an app with the given options
        """
        from nereid import Nereid
        options['DATABASE_NAME'] = self.db_name
        options['DEBUG'] = True
        return Nereid(**options)


# An instance of testing module which can be used inside test cases
testing_proxy = TestingProxy()


@testing_proxy.register()
def create_company(obj, name, currency='USD'):
    """Creates a new company and returns the ID
    """
    company_obj = obj.pool.get('company.company')
    currency_obj = obj.pool.get('currency.currency')
    currency_id, = currency_obj.search([('code', '=', currency)], limit=1)
    return company_obj.create({'name': name, 'currency': currency_id})



@testing_proxy.register()
def create_user_party(obj, name, email, password, **kwargs):
    """Creates a user with given data

    :param kwargs: All extra arguments are treated as data for party
    """
    party_obj = obj.pool.get('party.party')
    address_obj = obj.pool.get('party.address')
    contact_mechanism_obj = obj.pool.get('party.contact_mechanism')

    kwargs['name'] = name
    party_id = party_obj.create(kwargs)
    party = party_obj.browse(party_id)

    email_id = contact_mechanism_obj.create({
        'type': 'email',
        'value': email,
        'party': party_id,
        })
    address_obj.write(party.addresses[0].id, {
        'name': name + 'Address',
        'password': password,
        'email': email_id,
        'party': party_id,
        })

    return party.addresses[0].id


@testing_proxy.register()
def create_guest_user(obj, name='Guest', email='guest@example.com', **options):
    """Create guest user
    """
    return obj.create_user_party(name, email, 'password', **options)


@testing_proxy.register()
def create_template(obj, name, source, site=False, lang_code='en_US'):
    """Creates and returns template ID
    """
    lang_obj = obj.pool.get('ir.lang')
    template_obj = obj.pool.get('nereid.template')

    return template_obj.create({
        'name': name,
        'source': source,
        'language': lang_obj.search([('code', '=', lang_code)], limit=1)[0],
        'website': site,
        })


@testing_proxy.register()
def create_site(obj, name, url_map=None, company=None, **options):
    """Create a site."""
    company_obj = obj.pool.get('company.company')
    site_obj = obj.pool.get('nereid.website')
    url_map_obj = obj.pool.get('nereid.url_map')
    lang_obj = obj.pool.get('ir.lang')

    options['name'] = name

    if url_map is None:
        url_map, = url_map_obj.search([], limit=1)
    options['url_map'] = url_map

    if company is None:
        company, = company_obj.search([], limit=1)
    options['company'] = company

    if 'default_language' not in options:
        options['default_language'], = lang_obj.search(
            [('code', '=', 'en_US')])

    return site_obj.create(options)


@testing_proxy.register()
def set_company_for_user(self, user, company):
    """Set company for current user"""
    user_obj = self.pool.get('res.user')
    return user_obj.write(user, {
        'main_company': company,
        'company': company
        })
