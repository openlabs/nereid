#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from __future__ import with_statement

import os  # noqa
import warnings

from flask import Flask
from flask.config import ConfigAttribute
from flask.globals import _request_ctx_stack
from flask.helpers import locked_cached_property
from jinja2 import MemcachedBytecodeCache
from werkzeug.routing import Submount, Map
from werkzeug import import_string

from .wrappers import Request, Response
from .backend import TransactionManager
from .session import NereidSessionInterface
from .templating import nereid_default_template_ctx_processor, \
    NEREID_TEMPLATE_FILTERS, ModuleTemplateLoader, LazyRenderer
from .helpers import url_for
from .ctx import RequestContext
from .exceptions import WebsiteNotFound


class Nereid(Flask):
    """
    ...

    Unlike typical web frameworks and their APIs, nereid depends more on
    configuration and not direct python modules written along the APIs
    Most of the functional code will remain on the modules installed on
    Tryton, and the database configurations.

    ...

    """
    #: The class that is used for request objects.  See
    #: :class:`~nereid.wrappers.Request`
    #: for more information.
    request_class = Request

    #: The class that is used for response objects.  See
    #: :class:`~nereid.wrappers.Response` for more information.
    response_class = Response

    #: the session interface to use.  By default an instance of
    #: :class:`~nereid.session.NereidSessionInterface` is used here.
    session_interface = NereidSessionInterface()

    #: An internal attribute to hold the Tryton model pool to avoid being
    #: initialised at every request as it is quite expensive to do so.
    #: To access the pool from modules, use the :meth:`pool`
    _pool = None

    #: The attribute holds a connection to the database backend.
    _database = None

    #: Configuration file for Tryton. The path to the configuration file
    #: can be specified and will be loaded when the application is
    #: initialised
    tryton_configfile = ConfigAttribute('TRYTON_CONFIG')

    #: The location where the translations of the template are stored
    translations_path = ConfigAttribute('TRANSLATIONS_PATH')

    #: The name of the database to connect to on initialisation
    database_name = ConfigAttribute('DATABASE_NAME')

    #: The default timeout to use if the timeout is not explicitly
    #: specified in the set or set many argument
    cache_default_timeout = ConfigAttribute('CACHE_DEFAULT_TIMEOUT')

    #: the maximum number of items the cache stores before it starts
    #: deleting some items.
    #: Applies for: SimpleCache, FileSystemCache
    cache_threshold = ConfigAttribute('CACHE_THRESHOLD')

    #: a prefix that is added before all keys. This makes it possible
    #: to use the same memcached server for different applications.
    #: Applies for: MecachedCache, GAEMemcachedCache
    #: If key_prefix is none the value of site is used as key
    cache_key_prefix = ConfigAttribute('CACHE_KEY_PREFIX')

    #: a list or tuple of server addresses or alternatively a
    #: `memcache.Client` or a compatible client.
    cache_memcached_servers = ConfigAttribute('CACHE_MEMCACHED_SERVERS')

    #: The directory where cache files are stored if FileSystemCache is used
    cache_dir = ConfigAttribute('CACHE_DIR')

    #: The type of cache to use. The type must be a full specification of
    #: the module so that an import can be made. Examples for werkzeug
    #: backends are given below
    #:
    #:  NullCache - werkzeug.contrib.cache.NullCache (default)
    #:  SimpleCache - werkzeug.contrib.cache.SimpleCache
    #:  MemcachedCache - werkzeug.contrib.cache.MemcachedCache
    #:  GAEMemcachedCache -  werkzeug.contrib.cache.GAEMemcachedCache
    #:  FileSystemCache - werkzeug.contrib.cache.FileSystemCache
    cache_type = ConfigAttribute('CACHE_TYPE')

    #: If a custom cache backend unknown to Nereid is used, then
    #: the arguments that are needed for the initialisation
    #: of the cache could be passed here as a `dict`
    cache_init_kwargs = ConfigAttribute('CACHE_INIT_KWARGS')

    #: boolean attribute to indicate if the initialisation of backend
    #: connection and other nereid support features are loaded. The
    #: application can work only after the initialisation is done.
    #: It is not advisable to set this manually, instead call the
    #: :meth:`initialise`
    initialised = False

    #: Prefix the name of the website to the template name sutomatically
    #: This feature would be deprecated in future in lieu of writing
    #: Jinja2 Loaders which could offer this behavior. This is set to False
    #: by default. For backward compatibility of loading templates from
    #: a template folder which has website names as subfolders, set this
    #: to True
    #:
    #: .. versionadded:: 2.8.0.4
    template_prefix_website_name = ConfigAttribute(
        'TEMPLATE_PREFIX_WEBSITE_NAME'
    )

    def __init__(self, **config):
        """
        The import_name is forced into `Nereid`
        """
        super(Nereid, self).__init__('nereid', **config)

        # Create the Map again because we do not want the static URL that
        # flask creates which is website agnostic.
        self.url_map = Map()

        # Update the defaults for config attributes introduced by nereid
        self.config.update({
            'TRYTON_CONFIG': None,

            'TEMPLATE_PREFIX_WEBSITE_NAME': True,

            'CACHE_TYPE': 'werkzeug.contrib.cache.NullCache',
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_THRESHOLD': 500,
            'CACHE_INIT_KWARGS': {},
            'CACHE_KEY_PREFIX': '',
        })

    def initialise(self):
        """
        The application needs initialisation to load the database
        connection etc. In previous versions this was done with the
        initialisation of the class in the __init__ method. This is
        now separated into this function.
        """
        #: Check if the secret key is defined, if not raise an
        #: exception since it is required
        assert self.secret_key, 'Secret Key is not defined in config'

        #: Load the cache
        self.load_cache()

        #: A dictionary of the website names to spec of the website in the
        #: backend. This is loaded by :meth:`load_websites` when the app is
        #: initialised and all future lookups are made on this dictionary.
        #: The specs include the following information
        #:
        #:  1. id - ID of the website in the backend
        #:  2. url_map - The loaded url_map of the website
        #:
        #: .. tip:
        #:  If a new website is introduced a reload of the application would
        #:  be necessary for it to reflect here
        self.websites = {}

        # Backend initialisation
        self.load_backend()
        with self.root_transaction:
            self.load_websites()
            self.add_ctx_processors_from_db()

        # Add the additional template context processors
        self.template_context_processors[None].append(
            nereid_default_template_ctx_processor
        )

        # Finally set the initialised attribute
        self.initialised = True

    def load_cache(self):
        """
        Load the cache and assign the Cache interface to
        """
        BackendClass = import_string(self.cache_type)

        if self.cache_type == 'werkzeug.contrib.cache.NullCache':
            self.cache = BackendClass(self.cache_default_timeout)
        elif self.cache_type == 'werkzeug.contrib.cache.SimpleCache':
            self.cache = BackendClass(
                self.cache_threshold, self.cache_default_timeout)
        elif self.cache_type == 'werkzeug.contrib.cache.MemcachedCache':
            self.cache = BackendClass(
                self.cache_memcached_servers,
                self.cache_default_timeout,
                self.cache_key_prefix)
        elif self.cache_type == 'werkzeug.contrib.cache.GAEMemcachedCache':
            self.cache = BackendClass(
                self.cache_default_timeout,
                self.cache_key_prefix)
        elif self.cache_type == 'werkzeug.contrib.cache.FileSystemCache':
            self.cache = BackendClass(
                self.cache_dir,
                self.cache_threshold,
                self.cache_default_timeout)
        else:
            self.cache = BackendClass(**self.cache_init_kwargs)

    def load_backend(self):
        """
        This method loads the configuration file if specified and
        also connects to the backend, initialising the pool on the go
        """
        if self.tryton_configfile is not None:
            from trytond.config import CONFIG
            CONFIG.update_etc(self.tryton_configfile)
            CONFIG.set_timezone()

        from trytond import backend
        from trytond.modules import register_classes
        register_classes()
        from trytond.pool import Pool

        # Load and initialise pool
        Database = backend.get('Database')
        self._database = Database(self.database_name).connect()
        self._pool = Pool(self.database_name)
        self._pool.init()

    @property
    def pool(self):
        """
        A proxy to the _pool
        """
        return self._pool

    @property
    def database(self):
        """
        Return connection to Database backend of tryton
        """
        return self._database

    @property
    def root_transaction(self):
        """
        Allows the use of the transaction as a context manager with the
        root user.

        .. versionadded::0.3
        """
        return TransactionManager(self.database_name, 0, None)

    def get_method(self, model_method):
        """
        Get the object from pool and fetch the method from it

        model_method is expected to be '<model>.<method>'. The returned
        function/method object can be stored in the endpoint map for a
        faster lookup and response rather than looking it up at request
        time.
        """
        model_method_split = model_method.split('.')
        model = '.'.join(model_method_split[:-1])
        method = model_method_split[-1]

        try:
            return getattr(self.pool.get(model), method)
        except AttributeError:
            raise Exception("Method %s not in Model %s" % (method, model))

    def load_websites(self):
        """
        Load the websites and build a map of the website names to the ID
        in database for quick connection to the website
        """
        Website = self.pool.get("nereid.website")

        for website in Website.search([]):
            url_rules = []

            # Add the static url
            url_rules.append(
                self.url_rule_class(
                    self.static_url_path + '/<path:filename>',
                    endpoint='static',
                    host=website.name,
                )
            )

            for url_kwargs in website.url_map.get_rules_arguments():
                rule = self.url_rule_class(
                    url_kwargs.pop('rule'),
                    host=website.name,
                    **url_kwargs
                )
                rule.provide_automatic_options = True
                url_rules.append(rule)   # Add rule to map
                if (not url_kwargs['build_only']) \
                        and not(url_kwargs['redirect_to']):
                    # Add the method to the view_functions list if the
                    # endpoint was not a build_only url
                    self.view_functions[url_kwargs['endpoint']] = \
                        self.get_method(url_kwargs['endpoint'])

            if website.locales:
                # Create the URL map with locale prefix
                self.url_map.add(
                    self.url_rule_class(
                        '/',
                        redirect_to='/%s' % website.default_locale.code,
                        host=website.name
                    ),
                )
                self.url_map.add(Submount('/<locale>', url_rules))
            else:
                # Create a new map with the given URLs
                map(self.url_map.add, url_rules)

            self.websites[website.name] = {
                'id': website.id,
                'name': website.name,
                'application_user': website.application_user.id,
                'guest_user': website.guest_user.id,
                'company': website.company.id,
            }

        # Finally add the view_function for static
        self.view_functions['static'] = self.send_static_file

    def add_ctx_processors_from_db(self):
        """
        Adds template context processors registers with the model
        nereid.template.context_processor
        """
        ctx_processor_obj = self.pool.get('nereid.template.context_processor')

        db_ctx_processors = ctx_processor_obj.get_processors()
        if None in db_ctx_processors:
            self.template_context_processors[None].extend(
                db_ctx_processors.pop(None)
            )
        self.template_context_processors.update(db_ctx_processors)

    def request_context(self, environ):
        return RequestContext(self, environ)

    def full_dispatch_request(self):
        """
        Ensure that the full_dispatch_request is handled around a transaction
        """
        from trytond.transaction import Transaction
        from trytond.pool import Pool

        req = _request_ctx_stack.top.request
        if req.routing_exception is not None:
            self.raise_routing_exception(req)

        try:
            with Transaction().start(
                self.database_name, 0, readonly=True
            ):
                # TODO: Make finding website faster by using a cache ?
                Website = Pool().get('nereid.website')
                website, = Website.search([('name', '=', req.url_rule.host)])
                # Construct a dictionary since Active records are not
                # usable outside the transaction
                website = {
                    'id': website.id,
                    'application_user': website.application_user.id,
                    'company': website.company.id,
                }
        except ValueError:
            raise WebsiteNotFound()

        with Transaction().start(
                self.database_name,
                website['application_user'],
                context={'company': website['company']}) as txn:
            try:
                rv = super(Nereid, self).full_dispatch_request()
                txn.cursor.commit()
            except Exception:
                txn.cursor.rollback()
                raise
            else:
                return rv

    def dispatch_request(self):
        """
        Does the request dispatching.  Matches the URL and returns the
        return value of the view or error handler.  This does not have to
        be a response object.
        """
        from trytond.pool import Pool
        from trytond.transaction import Transaction

        req = _request_ctx_stack.top.request
        if req.routing_exception is not None:
            self.raise_routing_exception(req)

        rule = req.url_rule
        # if we provide automatic options for this URL and the
        # request came with the OPTIONS method, reply automatically
        if getattr(rule, 'provide_automatic_options', False) \
           and req.method == 'OPTIONS':
            return self.make_default_options_response()

        language = 'en_US'
        if req.nereid_website:
            # If this is a request specific to a website
            # then take the locale from the website
            language = req.nereid_locale.language.code

        with Transaction().set_context(language=language):

            # pop locale if specified in the view_args
            req.view_args.pop('locale', None)

            # otherwise dispatch to the handler for that endpoint
            meth = self.view_functions[rule.endpoint]
            if not hasattr(meth, 'im_self') or meth.im_self:
                # static or class method
                result = meth(**req.view_args)
            else:
                # instance method, extract active_id from the url
                # arguments and pass the model instance as first argument
                model = Pool().get(rule.endpoint.rsplit('.', 1)[0])
                i = model(req.view_args.pop('active_id'))
                result = meth(i, **req.view_args)

            if isinstance(result, LazyRenderer):
                result = unicode(result)

            return result

    def create_jinja_environment(self):
        """
        Extend the default jinja environment that is created. Also
        the environment returned here should be specific to the current
        website.
        """
        rv = super(Nereid, self).create_jinja_environment()

        # Add the custom extensions specific to nereid
        rv.add_extension('jinja2.ext.i18n')
        rv.add_extension('nereid.templating.FragmentCacheExtension')

        rv.filters.update(**NEREID_TEMPLATE_FILTERS)

        # add the locale sensitive url_for of nereid
        rv.globals.update(url_for=url_for)

        if self.cache:
            # Setup the bytecode cache
            rv.bytecode_cache = MemcachedBytecodeCache(self.cache)
            # Setup for fragmented caching
            rv.fragment_cache = self.cache
            rv.fragment_cache_prefix = self.cache_key_prefix + "-frag-"

        return rv

    @locked_cached_property
    def jinja_loader(self):
        """
        Creates the loader for the Jinja2 Environment
        """
        return ModuleTemplateLoader(
            self.database_name, searchpath=self.template_folder,
        )

    def select_jinja_autoescape(self, filename):
        """
        Returns `True` if autoescaping should be active for the given
        template name.
        """
        if filename is None:
            return False
        if filename.endswith(('.jinja',)):
            return True
        return super(Nereid, self).select_jinja_autoescape(filename)

    @property
    def guest_user(self):
        warnings.warn(DeprecationWarning(
            "guest_user as an attribute will be deprecated.\n"
            "Use request.nereid_website.guest_user.id instead"
        ))
        from .globals import request
        return request.nereid_website.guest_user.id
