# -*- coding: UTF-8 -*-
'''
    nereid.routing

    URLs, Routes and Maps

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''

from werkzeug.exceptions import HTTPException, MethodNotAllowed
from werkzeug.routing import Rule, Map

from .config import ConfigAttribute
from .helpers import send_from_directory
from .globals import _request_ctx_stack, request


class RoutingMixin(object):
    """Mixin object for Routing"""

    #: Path for the static files.  If you don't want to use static files
    #: you can set this value to `None` in which case no URL rule is added
    #: and the development server will no longer serve any static files.
    #:
    #: This is the default used for application and modules unless a
    #: different value is passed to the constructor.
    static_path = '/static'

    #: The location from where static files will be served
    static_fileroot = ConfigAttribute('STATIC_FILEROOT')

    #: Enable this if you want to use the X-Sendfile feature.  Keep in
    #: mind that the server has to support this.  This only affects files
    #: sent with the :func:`send_file` method.
    #:
    #: This attribute can also be configured from the config with the
    #: `USE_X_SENDFILE` configuration key.  Defaults to `False`.
    use_x_sendfile = ConfigAttribute('USE_X_SENDFILE')

    #: The _name of the model in the backend which holds the Site 
    #: information.
    website_model = ConfigAttribute('WEBSITE_MODEL')

    def __init__(self, **config):
        #: A dictionary of all view functions registered.  The keys will
        #: be model.function names which are also used to generate URLs and
        #: the values are the method objects themselves.
        self.view_functions = { }

        #: The :class:`~werkzeug.routing.Map` for this instance.  You can use
        #: this to change the routing converters after the class was created
        #: but before any routes are connected.  Example::
        #:
        #:    from werkzeug.routing import BaseConverter
        #:
        #:    class ListConverter(BaseConverter):
        #:        def to_python(self, value):
        #:            return value.split(',')
        #:        def to_url(self, values):
        #:            return ','.join(BaseConverter.to_url(value)
        #:                            for value in values)
        #:
        #:    app = Flask(__name__)
        #:    app.url_map.converters['list'] = ListConverter
        self.url_map = Map()

        # register the static folder for the application.  Do that even
        # if the folder does not exist.  First of all it might be created
        # while the server is running (usually happens during development)
        # but also because google appengine stores static files somewhere
        # else when mapped with the .yml file.
        self.add_url_rule(self.static_path + '/<path:filename>',
                          endpoint='static',
                          view_func=self.send_static_file)

    def dispatch_request(self):
        """Does the request dispatching.  Matches the URL and returns the
        return value of the view or error handler.  This does not have to
        be a response object.
        """
        from trytond.transaction import Transaction
        req = _request_ctx_stack.top.request
        try:
            if req.routing_exception is not None:
                raise req.routing_exception
            rule = req.url_rule

            # if we provide automatic options for this URL and the
            # request came with the OPTIONS method, reply automatically
            if rule.provide_automatic_options and req.method == 'OPTIONS':
                return self.make_default_options_response()
            # otherwise dispatch to the handler for that endpoint
            language = req.view_args.pop(
                'language', req.nereid_website.default_language.code)
            with Transaction().set_context(language=language):
                return self.view_functions[rule.endpoint](**req.view_args)

        except HTTPException, exception:
            return self.handle_http_exception(exception)

    def make_default_options_response(self):
        """This method is called to create the default `OPTIONS` response.
        This can be changed through subclassing to change the default
        behaviour of `OPTIONS` responses.
        """
        methods = []
        try:
            _request_ctx_stack.top.url_adapter.match(method='--')
        except MethodNotAllowed, exception:
            methods = exception.valid_methods
        except HTTPException, exception:
            pass
        result = self.response_class()
        result.allow.update(methods)
        return result

    def make_response(self, result):
        """Converts the return value from a view function to a real
        response object that is an instance of :attr:`response_class`.

        The following types are allowed for `rv`:

        .. tabularcolumns:: |p{3.5cm}|p{9.5cm}|

        ======================= ===========================================
        :attr:`response_class`  the object is returned unchanged
        :class:`str`            a response object is created with the
                                string as body
        :class:`unicode`        a response object is created with the
                                string encoded to utf-8 as body
        :class:`tuple`          the response object is created with the
                                contents of the tuple as arguments
        a WSGI function         the function is called as WSGI application
                                and buffered as response object
        ======================= ===========================================

        :param rv: the return value from the view function
        """
        if result is None:
            raise ValueError('View function did not return a response')
        if isinstance(result, self.response_class):
            return result
        if isinstance(result, basestring):
            return self.response_class(result)
        if isinstance(result, tuple):
            return self.response_class(*result)
        return self.response_class.force_type(result, request.environ)

    def create_url_adapter(self, request_):
        """Creates a URL adapter for the given request.  The URL adapter
        is created at a point where the request context is not yet set up
        so the request is passed explicitly.

        """
        return self.url_map.bind_to_environ(
            request_.environ,
            server_name=self.config['SERVER_NAME']
            )

    def add_url_rule(self, rule, endpoint, view_func=None, **options):
        """Connects a URL rule.  Works exactly like the :meth:`route`
        decorator.  If a view_func is provided it will be registered with the
        endpoint.

        :param rule: the URL rule as string
        :param endpoint: the endpoint for the registered URL rule. Nereid 
                         itself assumes the name of the view function as
                         endpoint
        :param view_func: the function to call when serving a request to the
                          provided endpoint
        :param options: the options to be forwarded to the underlying
                        :class:`~werkzeug.routing.Rule` object.  A change
                        to Werkzeug is handling of method options.  methods
                        is a list of methods this rule should be limited
                        to (`GET`, `POST` etc.).  By default a rule
                        just listens for `GET` (and implicitly `HEAD`).
                        `OPTIONS` is implicitly added and handled by the 
                        standard request handling.
        """
        options['endpoint'] = endpoint

        methods = options.pop('methods', ('GET',))
        provide_automatic_options = False
        if 'OPTIONS' not in methods:
            methods = tuple(methods) + ('OPTIONS',)
            provide_automatic_options = True

        rule = Rule(rule, methods=methods, **options)
        rule.provide_automatic_options = provide_automatic_options
        self.url_map.add(rule)

        if view_func is not None:
            self.view_functions[endpoint] = view_func

    def send_static_file(self, filename):
        """Function used internally to send static files from the static
        folder to the browser.
        """
        return send_from_directory(self.static_fileroot, filename)

    def add_urls_from_db(self):
        """
        Add the URLs from the backend database
        """
        with self.transaction:
            website_obj = self.pool.get(self.website_model)
            urls = website_obj.get_urls(self.site)

            for url in urls:
                view_func = None
                if (not url['build_only']) and not(url['redirect_to']):
                    view_func = self.get_method(url['endpoint'])
                self.add_url_rule(view_func=view_func, **url)

