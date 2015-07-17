# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from __future__ import with_statement

import os  # noqa
import warnings
import inspect

from flask import Flask
from flask.config import ConfigAttribute
from flask.globals import _request_ctx_stack, current_app
from flask.helpers import locked_cached_property
from jinja2 import MemcachedBytecodeCache
from werkzeug import import_string, abort
import flask.ext.login
from flask.ext.login import LoginManager
from flask.ext.babel import Babel

from trytond import backend
from trytond.pool import Pool
from trytond.cache import Cache
from trytond.config import config
from trytond.exceptions import UserError
from trytond.modules import register_classes
from trytond.transaction import Transaction

from .wrappers import Request, Response
from .session import NereidSessionInterface
from .templating import nereid_default_template_ctx_processor, \
    NEREID_TEMPLATE_FILTERS, ModuleTemplateLoader, LazyRenderer
from .helpers import url_for, root_transaction_if_required
from .ctx import RequestContext
from .csrf import NereidCsrfProtect
from .signals import transaction_start, transaction_stop
from .routing import Rule


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

    #: The rule object to use for URL rules created.  This is used by
    #: :meth:`add_url_rule`.  Defaults to :class:`nereid.routing.Rule`.
    #:
    #: .. versionadded:: 3.2.0.9
    url_rule_class = Rule

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

    #: Load the template eagerly. This would render the template
    #: immediately and still return a LazyRenderer. This is useful
    #: in debugging issues that may be hard to debug with lazy rendering
    eager_template_render = ConfigAttribute('EAGER_TEMPLATE_RENDER')

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

    #: Time in seconds for which the token is valid.
    token_validity_duration = ConfigAttribute(
        'TOKEN_VALIDITY_DURATION'
    )

    def __init__(self, **config):
        """
        The import_name is forced into `Nereid`
        """
        super(Nereid, self).__init__('nereid', **config)

        # Update the defaults for config attributes introduced by nereid
        self.config.update({
            'TRYTON_CONFIG': None,
            'TEMPLATE_PREFIX_WEBSITE_NAME': True,
            'TOKEN_VALIDITY_DURATION': 60 * 60,

            'CACHE_TYPE': 'werkzeug.contrib.cache.NullCache',
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_THRESHOLD': 500,
            'CACHE_INIT_KWARGS': {},
            'CACHE_KEY_PREFIX': '',

            'EAGER_TEMPLATE_RENDER': False,
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

        #: Initialise the CSRF handling
        self.csrf_protection = NereidCsrfProtect()
        self.csrf_protection.init_app(self)

        self.view_functions['static'] = self.send_static_file

        # Backend initialisation
        self.load_backend()

        #: Initialise the login handler
        login_manager = LoginManager()
        login_manager.user_loader(self._pool.get('nereid.user').load_user)
        login_manager.header_loader(
            self._pool.get('nereid.user').load_user_from_header
        )
        login_manager.token_loader(
            self._pool.get('nereid.user').load_user_from_token
        )
        login_manager.unauthorized_handler(
            self._pool.get('nereid.user').unauthorized_handler
        )
        login_manager.login_view = "nereid.website.login"
        login_manager.anonymous_user = self._pool.get('nereid.user.anonymous')
        login_manager.init_app(self)

        self.login_manager = login_manager

        # Monkey patch the url_for method from flask-login to use
        # the nereid specific url_for
        flask.ext.login.url_for = url_for

        self.template_context_processors[None].append(
            self.get_context_processors()
        )

        # Add the additional template context processors
        self.template_context_processors[None].append(
            nereid_default_template_ctx_processor
        )

        # Add template_filters registered using decorator
        for name, function in self.get_template_filters():
            self.jinja_env.filters[name] = function

        # Initialize Babel
        Babel(self)

        # Finally set the initialised attribute
        self.initialised = True

    def get_urls(self):
        """
        Return the URL rules for routes formed by decorating methods with the
        :func:`~nereid.helpers.route` decorator.

        This method goes through all the models and their methods in the pool
        of the loaded database and looks for the `_url_rules` attribute in
        them. If there are URLs defined, it is added to the url map.
        """
        rules = []
        models = Pool._pool[self.database_name]['model']

        for model_name, model in models.iteritems():
            for f_name, f in inspect.getmembers(
                    model, predicate=inspect.ismethod):

                if not hasattr(f, '_url_rules'):
                    continue

                for rule in f._url_rules:
                    rule_obj = self.url_rule_class(
                        rule[0],
                        endpoint='.'.join([model_name, f_name]),
                        **rule[1]
                    )
                    rules.append(rule_obj)
                    if rule_obj.is_csrf_exempt:
                        self.csrf_protection._exempt_views.add(
                            rule_obj.endpoint
                        )

        return rules

    @root_transaction_if_required
    def get_context_processors(self):
        """
        Returns the method object which wraps context processor methods
        formed by decorating methods with the
        :func:`~nereid.helpers.context_processor` decorator.

        This method goes through all the models and their methods in the pool
        of the loaded database and looks for the `_context_processor` attribute
        in them and adds to context_processor dict.
        """
        context_processors = {}
        models = Pool._pool[self.database_name]['model']

        for model_name, model in models.iteritems():
            for f_name, f in inspect.getmembers(
                    model, predicate=inspect.ismethod):

                if hasattr(f, '_context_processor'):
                    ctx_proc_as_func = getattr(Pool().get(model_name), f_name)
                    context_processors[ctx_proc_as_func.func_name] = \
                        ctx_proc_as_func

        def get_ctx():
            """Returns dictionary having method name in keys and method object
            in values.
            """
            return context_processors

        return get_ctx

    @root_transaction_if_required
    def get_template_filters(self):
        """
        Returns a list of name, function pairs for template filters registered
        in the models using :func:`~nereid.helpers.template_filter` decorator.
        """
        models = Pool._pool[self.database_name]['model']
        filters = []

        for model_name, model in models.iteritems():
            for f_name, f in inspect.getmembers(
                    model, predicate=inspect.ismethod):

                if hasattr(f, '_template_filter'):
                    filter = getattr(Pool().get(model_name), f_name)
                    filters.append((filter.func_name, filter))

        return filters

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
            warnings.warn(DeprecationWarning(
                'TRYTON_CONFIG configuration will be deprecated in future.'
            ))
            config.update_etc(self.tryton_configfile)

        register_classes()

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

    def request_context(self, environ):
        return RequestContext(self, environ)

    @root_transaction_if_required
    def create_url_adapter(self, request):
        """Creates a URL adapter for the given request.  The URL adapter
        is created at a point where the request context is not yet set up
        so the request is passed explicitly.

        """
        if request is not None:

            Website = Pool().get('nereid.website')

            website = Website.get_from_host(request.host)
            rv = website.get_url_adapter(self).bind_to_environ(
                request.environ,
                server_name=self.config['SERVER_NAME']
            )
            return rv

    def dispatch_request(self):
        """
        Does the request dispatching.  Matches the URL and returns the
        return value of the view or error handler.  This does not have to
        be a response object.
        """
        DatabaseOperationalError = backend.get('DatabaseOperationalError')

        req = _request_ctx_stack.top.request
        if req.routing_exception is not None:
            self.raise_routing_exception(req)

        rule = req.url_rule
        # if we provide automatic options for this URL and the
        # request came with the OPTIONS method, reply automatically
        if getattr(rule, 'provide_automatic_options', False) \
           and req.method == 'OPTIONS':
            return self.make_default_options_response()

        with Transaction().start(self.database_name, 0):
            Cache.clean(self.database_name)
            Cache.resets(self.database_name)

        with Transaction().start(self.database_name, 0, readonly=True):
            Website = Pool().get('nereid.website')
            website = Website.get_from_host(req.host)

            user = website.application_user.id
            website_context = website.get_context()
            website_context.update({
                'company': website.company.id,
            })

            language = 'en_US'
            if website:
                # If this is a request specific to a website
                # then take the locale from the website
                language = website.get_current_locale(req).language.code

        # pop locale if specified in the view_args
        req.view_args.pop('locale', None)
        active_id = req.view_args.pop('active_id', None)

        for count in range(int(config.get('database', 'retry')), -1, -1):
            with Transaction().start(
                    self.database_name, user,
                    context=website_context,
                    readonly=rule.is_readonly) as txn:
                try:
                    transaction_start.send(self)
                    rv = self._dispatch_request(
                        req, language=language, active_id=active_id
                    )
                    txn.cursor.commit()
                except DatabaseOperationalError:
                    # Strict transaction handling may cause this.
                    # Rollback and Retry the whole transaction if within
                    # max retries, or raise exception and quit.
                    txn.cursor.rollback()
                    if count:
                        continue
                    raise
                except Exception:
                    # Rollback and raise any other exception
                    txn.cursor.rollback()
                    raise
                else:
                    return rv
                finally:
                    transaction_stop.send(self)

    def _dispatch_request(self, req, language, active_id):
        """
        Implement the nereid specific _dispatch
        """
        with Transaction().set_context(language=language):

            # otherwise dispatch to the handler for that endpoint
            if req.url_rule.endpoint in self.view_functions:
                meth = self.view_functions[req.url_rule.endpoint]
            else:
                model, method = req.url_rule.endpoint.rsplit('.', 1)
                meth = getattr(Pool().get(model), method)

            if not hasattr(meth, 'im_self') or meth.im_self:
                # static or class method
                result = meth(**req.view_args)
            else:
                # instance method, extract active_id from the url
                # arguments and pass the model instance as first argument
                model = Pool().get(req.url_rule.endpoint.rsplit('.', 1)[0])
                i = model(active_id)
                try:
                    i.rec_name
                except UserError:
                    # The record may not exist anymore which results in
                    # a read error
                    current_app.logger.debug(
                        "Record %s doesn't exist anymore." % i
                    )
                    abort(404)
                result = meth(i, **req.view_args)

            if isinstance(result, LazyRenderer):
                result = (
                    unicode(result), result.status, result.headers
                )

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

        # Install the gettext callables
        from .contrib.locale import TrytonTranslations
        translations = TrytonTranslations(module=None, ttype='nereid_template')
        rv.install_gettext_callables(
            translations.gettext, translations.ngettext
        )
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
