# -*- coding: UTF-8 -*-
'''
    nereid

    A fullstack web framework based on Flask, but powered by Tryton

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher
    :license: BSD, see LICENSE for more details
'''
from __future__ import with_statement

import os
import sys
from threading import Lock
from datetime import timedelta
from itertools import chain

from werkzeug import ImmutableDict
from werkzeug.exceptions import InternalServerError

from .wrappers import Request, Response
from .config import ConfigAttribute, Config
from .ctx import _RequestContext
from .globals import request, _request_ctx_stack, transaction
from .signals import request_started, request_finished, got_request_exception,\
    request_tearing_down

from .backend import BackendMixin
from .templating import TemplateMixin
from .routing import RoutingMixin
from .session import SessionMixin, Session, FilesystemSessionStore, _NullSession
from .cache import Cache, CacheMixin

# a lock used for logger initialization
_logger_lock = Lock()

# A global Cache
cache = Cache()


class Nereid(BackendMixin, RoutingMixin,
        TemplateMixin, SessionMixin, CacheMixin):
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

    #: The debug flag.  Set this to `True` to enable debugging of the
    #: application.  In debug mode the debugger will kick in when an unhandled
    #: exception ocurrs and the integrated server will automatically reload
    #: the application if changes in the code are detected.
    #:
    #: This attribute can also be configured from the config with the `DEBUG`
    #: configuration key.  Defaults to `False`.
    debug = ConfigAttribute('DEBUG')

    #: The testing flag.  Set this to `True` to enable the test mode of
    #: Flask extensions (and in the future probably also Flask itself).
    #: For example this might activate unittest helpers that have an
    #: additional runtime cost which should not be enabled by default.
    #:
    #: This attribute can also be configured from the config with the
    #: `TESTING` configuration key.  Defaults to `False`.
    testing = ConfigAttribute('TESTING')
    test_client_class = None

    #: The name of the logger to use.  By default the logger name is the
    #: package name passed to the constructor.
    logger_name = ConfigAttribute('LOGGER_NAME')

    #: The logging format used for the debug logger.  This is only used when
    #: the application is in debug mode, otherwise the attached logging
    #: handler does the formatting.
    debug_log_format = (
        '-' * 80 + '\n' +
        '%(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n' +
        '%(message)s\n' +
        '-' * 80
    )


    #: ID of the party.address to be used as a Guest account
    #: Defaults to None, Not specifying the GUEST USER will
    #: limit the application from performing certain tasks 
    #: whcih depend on request.nereid_user as it will return 
    #: None when the user is not Logged In
    guest_user = ConfigAttribute('GUEST_USER')

    root_path = ConfigAttribute('ROOT_PATH')
    site = ConfigAttribute('SITE')

    #: Default configuration parameters.
    default_config = ImmutableDict({
        'DEBUG': False,
        'TESTING': False,
        'PROPAGATE_EXCEPTIONS': None,

        'SESSION_COOKIE_NAME': 'session',
        'SESSION_STORE_CLASS': 'werkzeug.contrib.sessions.FilesystemSessionStore',
        'SESSION_CLASS': Session,
        'PERMANENT_SESSION_LIFETIME': timedelta(days=31),
        'SESSION_STORE_PATH': '/tmp',

        'USE_X_SENDFILE': False,
        'STATIC_FILEROOT': '',
        'LOGGER_NAME': None,
        'SERVER_NAME': None,
        'MAX_CONTENT_LENGTH': None,
        'ROOT_PATH': os.path.curdir,
        'SITE': None,
        'WEBSITE_MODEL': 'nereid.website',
        'TRYTON_USER': 1,
        'TRYTON_CONTEXT': {},
        'TRYTON_CONFIG': None,
        'GUEST_USER': None,

        # Cache Settings
        'CACHE_TYPE': 'werkzeug.contrib.cache.NullCache',
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_THRESHOLD': 500,
        'CACHE_INIT_KWARGS': {},
        'CACHE_KEY_PREFIX': None,

        # Template Settings
        'TEMPLATE_LOADER_CLASS': 'nereid.templating.TrytonTemplateLoader',
        # Specify this if you are using the nereid.templating.FileSystemLoader
        # Argument can be '/path/to/template' or ['path1', 'path2']
        'TEMPLATE_SEARCH_PATH': ''
    })

    def __init__(self, **config):
        #: Load configuration
        self.config = Config(self.default_config)
        self.config.update(config)

        #: Prepare the deferred setup of the logger.
        self._logger = None
        self.logger_name = 'NEREID'

        #: A dictionary of all registered error handlers.  The key is
        #: be the error code as integer, the value the function that
        #: should handle that error.
        #: To register a error handler, use the :meth:`errorhandler`
        #: decorator.
        self.error_handlers = {}

        #: A dictionary with lists of functions that should be called at the
        #: beginning of the request.  The key of the dictionary is the name of
        #: the module this function is active for, `None` for all requests.
        #: This can for example be used to open database connections or
        #: getting hold of the currently logged in user.  To register a
        #: function here, use the :meth:`before_request` decorator.
        self.before_request_funcs = {}

        #: A lists of functions that should be called at the beginning of the
        #: first request to this instance.  To register a function here, use
        #: the :meth:`before_first_request` decorator.
        #:
        #: .. versionadded:: 0.2
        self.before_first_request_funcs = []

        #: A dictionary with lists of functions that should be called after
        #: each request.  The key of the dictionary is the name of the module
        #: this function is active for, `None` for all requests.  This can for
        #: example be used to open database connections or getting hold of the
        #: currently logged in user.  To register a function here, use the
        #: :meth:`after_request` decorator.
        self.after_request_funcs = {}

        #: A dictionary with lists of functions that are called after
        #: each request, even if an exception has occurred. The key of the
        #: dictionary is the name of the blueprint this function is active for,
        #: `None` for all requests. These functions are not allowed to modify
        #: the request, and their return values are ignored. If an exception
        #: occurred while processing the request, it gets passed to each
        #: teardown_request function. To register a function here, use the
        #: :meth:`teardown_request` decorator.
        #:
        #: .. versionadded:: 0.2
        self.teardown_request_funcs = {}


        # tracks internally if the application already handled at least one
        # request.
        self._got_first_request = False
        self._before_request_lock = Lock()


        BackendMixin.__init__(self, **config) 
        RoutingMixin.__init__(self, **config)
        CacheMixin.__init__(self, **config)
        TemplateMixin.__init__(self, **config)
        SessionMixin.__init__(self, **config)

        self.add_ctx_processors_from_db()
        self.add_urls_from_db()

    @property
    def propagate_exceptions(self):
        """Returns the value of the `PROPAGATE_EXCEPTIONS` configuration
        value in case it's set, otherwise a sensible default is returned.

        .. versionadded:: 0.7
        """
        rv = self.config['PROPAGATE_EXCEPTIONS']
        if rv is not None:
            return rv
        return self.testing or self.debug

    @property
    def preserve_context_on_exception(self):
        """Returns the value of the `PRESERVE_CONTEXT_ON_EXCEPTION`
        configuration value in case it's set, otherwise a sensible default
        is returned.

        .. versionadded:: 0.7
        """
        rv = self.config['PRESERVE_CONTEXT_ON_EXCEPTION']
        if rv is not None:
            return rv
        return self.debug

    @property
    def got_first_request(self):
        """This attribute is set to `True` if the application started
        handling the first request.

        .. versionadded:: 0.2
        """
        return self._got_first_request


    def run(self, host='127.0.0.1', port=5000, **options):
        """Runs the application on a local development server.  If the
        :attr:`debug` flag is set the server will automatically reload
        for code changes and show a debugger in case an exception happened.

        If you want to run the application in debug mode, but disable the
        code execution on the interactive debugger, you can pass
        ``use_evalex=False`` as parameter.  This will keep the debugger's
        traceback screen active, but disable code execution.

        .. admonition:: Keep in Mind

           Nereid will suppress any server error with a generic error page
           unless it is in debug mode.  As such to enable just the
           interactive debugger without the code reloading, you have to
           invoke :meth:`run` with ``debug=True`` and ``use_reloader=False``.
           Setting ``use_debugger`` to `True` without being in debug mode
           won't catch any exceptions because there won't be any to
           catch.

        :param host: the hostname to listen on.  set this to ``'0.0.0.0'``
                     to have the server available externally as well.
        :param port: the port of the webserver
        :param options: the options to be forwarded to the underlying
                        Werkzeug server.  See :func:`werkzeug.run_simple`
                        for more information.
        """
        from werkzeug import run_simple
        if 'debug' in options:
            self.debug = options.pop('debug')
        options.setdefault('use_reloader', self.debug)
        options.setdefault('use_debugger', self.debug)
        return run_simple(host, port, self, **options)

    @property
    def logger(self):
        """A :class:`logging.Logger` object for this application.  The
        default configuration is to log to stderr if the application is
        in debug mode.  This logger can be used to (surprise) log messages.
        Here some examples::

            app.logger.debug('A value for debugging')
            app.logger.warning('A warning ocurred (%d apples)', 42)
            app.logger.error('An error occoured')

        """
        if self._logger and self._logger.name == self.logger_name:
            return self._logger
        with _logger_lock:
            if self._logger and self._logger.name == self.logger_name:
                return self._logger
            from .logging import create_logger
            self._logger = result = create_logger(self)
            return result

    def handle_http_exception(self, exception):
        """Handles an HTTP exception.  By default this will invoke the
        registered error handlers and fall back to returning the
        exception as response.

        """
        handler = self.error_handlers.get(exception.code)
        if handler is None:
            return exception
        return handler(exception)

    def handle_exception(self, exception):
        """Default exception handling that kicks in when an exception
        occours that is not catched.  In debug mode the exception will
        be re-raised immediately, otherwise it is logged and the handler
        for a 500 internal server error is used.  If no such handler
        exists, a default 500 internal server error message is displayed.

        """
        got_request_exception.send(self, exception=exception)
        transaction.cursor.rollback()
        handler = self.error_handlers.get(500)
        if self.propagate_exceptions:
            raise
        self.logger.exception('Exception on %s [%s]' % (
            request.path,
            request.method
        ))
        if handler is None:
            return InternalServerError()
        return handler(exception)

    def request_context(self, environ):
        """Creates a request context from the given environment and binds
        it to the current context.  This must be used in combination with
        the `with` statement because the request is only bound to the
        current context for the duration of the `with` block.

        Example usage::

            with app.request_context(environ):
                do_something_with(request)

        The object returned can also be used without the `with` statement
        which is useful for working in the shell.  The example above is
        doing exactly the same as this code::

            ctx = app.request_context(environ)
            ctx.push()
            try:
                do_something_with(request)
            finally:
                ctx.pop()

        The big advantage of this approach is that you can use it without
        the try/finally statement in a shell for interactive testing:

        >>> ctx = app.test_request_context()
        >>> ctx.bind()
        >>> request.path
        u'/'
        >>> ctx.unbind()

        :param environ: a WSGI environment
        """
        return _RequestContext(self, environ)

    def test_request_context(self, *args, **kwargs):
        """Creates a WSGI environment from the given values (see
        :func:`werkzeug.create_environ` for more information, this
        function accepts the same arguments).
        """
        from werkzeug import create_environ
        environ_overrides = kwargs.setdefault('environ_overrides', {})
        if self.config.get('SERVER_NAME'):
            server_name = self.config.get('SERVER_NAME')
            if ':' not in server_name:
                http_host, http_port = server_name, '80'
            else:
                http_host, http_port = server_name.split(':', 1)

            environ_overrides.setdefault('SERVER_NAME', server_name)
            environ_overrides.setdefault('HTTP_HOST', server_name)
            environ_overrides.setdefault('SERVER_PORT', http_port)
        return self.request_context(create_environ(*args, **kwargs))


    def preprocess_request(self):
        """Called before the actual request dispatching and will
        call every as :meth:`before_request` decorated function.
        If any of these function returns a value it's handled as
        if it was the return value from the view and further
        request handling is stopped.
        """
        funcs = self.before_request_funcs.get(None, ())
        mod = request.module
        if mod and mod in self.before_request_funcs:
            funcs = chain(funcs, self.before_request_funcs[mod])
        for func in funcs:
            result = func()
            if result is not None:
                return result

    def process_response(self, response):
        """Can be overridden in order to modify the response object
        before it's sent to the WSGI server.  By default this will
        call all the :meth:`after_request` decorated functions.

        :param response: a :attr:`response_class` object.
        :return: a new response object or the same, has to be an
                 instance of :attr:`response_class`.
        """
        ctx = _request_ctx_stack.top
        mod = ctx.request.module
        if not isinstance(ctx.session, _NullSession):
            self.save_session(ctx.session, response)
        funcs = ()
        if mod and mod in self.after_request_funcs:
            funcs = reversed(self.after_request_funcs[mod])
        if None in self.after_request_funcs:
            funcs = chain(funcs, reversed(self.after_request_funcs[None]))
        for handler in funcs:
            response = handler(response)
        return response

    def wsgi_app(self, environ, start_response):
        """The actual WSGI application.  This is not implemented in
        `__call__` so that middlewares can be applied without losing a
        reference to the class.  So instead of doing this::

            app = MyMiddleware(app)

        It's a better idea to do this instead::

            app.wsgi_app = MyMiddleware(app.wsgi_app)

        Then you still have the original application object around and
        can continue to call methods on it.

        :param environ: a WSGI environment
        :param start_response: a callable accepting a status code,
                               a list of headers and an optional
                               exception context to start the response
        """
        with self.request_context(environ):
            with self.transaction as transaction:
                _request_ctx_stack.top.transaction = transaction
                try:
                    request_started.send(self)
                    result = self.preprocess_request()
                    if result is None:
                        result = self.dispatch_request()
                    response = self.make_response(result)
                except Exception, exception:
                    response = self.make_response(
                        self.handle_exception(exception))
                try:
                    response = self.process_response(response)
                    transaction.cursor.commit()
                except Exception, exception:
                    response = self.make_response(
                        self.handle_exception(exception))
                request_finished.send(self, response=response)
                return response(environ, start_response)

    def __call__(self, environ, start_response):
        """Shortcut for :attr:`wsgi_app`."""
        return self.wsgi_app(environ, start_response)

    def test_client(self, use_cookies=True):
        """Creates a test client for this application.  For information
        about unit testing head over to :ref:`testing`.

        The test client can be used in a `with` block to defer the closing down
        of the context until the end of the `with` block.  This is useful if
        you want to access the context locals for testing::

            with app.test_client() as c:
                rv = c.get('/?vodka=42')
                assert request.args['vodka'] == '42'

        """
        cls = self.test_client_class
        if cls is None:
            from .testing import NereidClient as cls
        return cls(self, self.response_class, use_cookies=use_cookies)

    def do_teardown_request(self):
        """Called after the actual request dispatching and will
        call every as :meth:`teardown_request` decorated function.  This is
        not actually called by the :class:`Flask` object itself but is always
        triggered when the request context is popped.  That way we have a
        tighter control over certain resources under testing environments.
        """
        funcs = reversed(self.teardown_request_funcs.get(None, ()))
        bp = request.blueprint
        if bp is not None and bp in self.teardown_request_funcs:
            funcs = chain(funcs, reversed(self.teardown_request_funcs[bp]))
        exc = sys.exc_info()[1]
        for func in funcs:
            rv = func(exc)
            if rv is not None:
                return rv
        request_tearing_down.send(self)
