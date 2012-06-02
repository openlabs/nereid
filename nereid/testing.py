# -*- coding: utf-8 -*-
"""
    nereid.testing
    ~~~~~~~~~~~~~~

    Implements test support helpers.  This module is lazily imported
    and usually not used in production environments.

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: GPLv3, see LICENSE for more details.
"""
import new

import unittest2
from flask.helpers import locked_cached_property
from werkzeug import Client, EnvironBuilder
from nereid import _request_ctx_stack
from nereid.sessions import Session
from nereid.contrib.locale import Babel
from werkzeug.contrib.sessions import FilesystemSessionStore

from .templating import TrytonTemplateLoader


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

        if not isinstance(
                self.application.session_interface.session_store,
                FilesystemSessionStore):
            self.application.session_interface.session_store = \
                    FilesystemSessionStore('/tmp', session_class=Session)

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



class FailFastTextTestRunner(unittest2.TextTestRunner):
    """A subclass of TextTestRunner which fails fast by default
    """
    def _makeResult(self):
        """This method returns an instance of the TestResult which infact 
        handles the failfast behaviour in the core
        """
        rv = super(FailFastTextTestRunner, self)._makeResult()
        rv.failfast = True
        return rv


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


        self.user = 1
        self.context = None

        from trytond.pool import Pool
        from trytond.transaction import Transaction
        with Transaction().start(self.db_name, self.user, self.context) as txn:
            self.pool = Pool(self.db_name)
            self.pool.init()


        self.initialised = True

    def pool(self):
        from trytond.pool import Pool
        return Pool(self.db_name)

    def drop_database(self):
        """
        Drop the database that was used for testing
        """
        if not self.initialised:
            raise Exception("Cannot drop database when not initialised")
        from trytond.protocols.dispatcher import drop
        drop(self.db_name, 'admin')

    def install_module(self, module):
        if not self.initialised:
            self.init()
        from trytond.transaction import Transaction
        from trytond.pool import Pool
        with Transaction().start(self.db_name, self.user, self.context) as txn:
            module_obj = Pool().get('ir.module.module')
            lang_obj = Pool().get('ir.lang')

            modules = module_obj.search([('name', '=', module)])
            module_obj.install(modules)

            # Find modules to install and trigger pool to update them
            module_ids = module_obj.search([
                ('state', 'in', ['to upgrade', 'to remove', 'to install']),
                ])
            lang_ids = lang_obj.search([
                ('translatable', '=', True),
                ])
            lang = [x.code for x in lang_obj.browse(lang_ids)]
            Pool().init(update=True, lang=lang)
            txn.cursor.commit()

    def register(self, name=None):
        """A decorator that is used to register functions for being attached
        as helper method for testing

        .. code-block:: python

            @testing_proxy.register()
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
        from nereid import Nereid as NereidBase
        class Nereid(NereidBase):
            @locked_cached_property
            def jinja_loader(self):
                """Creates the loader for the Jinja2 Environment
                """
                return TrytonTemplateLoader(app)

        app = Nereid()
        app.config.update(options)
        app.config['DATABASE_NAME'] = self.db_name
        app.config['DEBUG'] = True
        app.session_interface.session_store = \
            FilesystemSessionStore('/tmp', session_class=Session)

        # Initialise the app now
        app.initialise()

        # Load babel as its a required extension anyway
        Babel(app)
        return app


# An instance of testing module which can be used inside test cases
testing_proxy = TestingProxy()


class TestCase(unittest2.TestCase):
    """
    A TestCase template that could be subclassed by test implementations

    Subclassing this gives automatic database creation on setupClass and drop
    of database at the end of execution of the TestCase.
    """

    @classmethod
    def setUpClass(cls):
        testing_proxy.init()

    @classmethod
    def tearDownClass(cls):
        testing_proxy.drop_database()


@testing_proxy.register()
def create_company(obj, name, currency='USD'):
    """Creates a new company and returns the ID
    """
    company_obj = obj.pool.get('company.company')
    currency_obj = obj.pool.get('currency.currency')

    currency_id, = currency_obj.search([('code', '=', currency)], limit=1)
    return company_obj.create({'name': name, 'currency': currency_id})


@testing_proxy.register()
def create_user_party(obj, name, email, password, company):
    """Creates a user with given data

    :param obj: The instance of :class:TestingProxy. This value need not be
                passed as the decorator automatically assigns this value
    :param name: The name for the user
    :param email: The email for the user (login)
    :param password: The password of the user
    :param company: The company to which the user must belong
    :return: ID of the created user
    """
    user_obj = obj.pool.get('nereid.user')

    return user_obj.create({
        'name': name,
        'email': email,
        'password': password,
        'company': company,
        })


@testing_proxy.register()
def create_guest_user(obj, name='Guest', email='guest@example.com',
        company=None):
    """Create guest user

    .. note::
        This is a wrapper around :py:func:`~create_user_party`

    :param obj: The instance of :class:TestingProxy. This value need not be
                passed as the decorator automatically assigns this value
    :param name: Name of the user, defaults to `Guest`
    :param email: Email of the user, defaults to `guest@example.com`
    :param company: The company to which the user must belong
    :return: ID of the created user
    """
    return obj.create_user_party(name, email, 'password', company)


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

    if 'application_user' not in options:
        options['application_user'] = 1

    return site_obj.create(options)


@testing_proxy.register()
def set_company_for_user(self, user, company):
    """Set company for current user"""
    user_obj = self.pool.get('res.user')
    return user_obj.write(user, {
        'main_company': company,
        'company': company
        })
