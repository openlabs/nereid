# -*- coding: UTF-8 -*-
'''
    nereid.templating

    Implements the Jinja2 bridge

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details
'''
from itertools import chain
from decimal import Decimal

from werkzeug import ImmutableDict
from werkzeug.utils import import_string
from jinja2 import Environment, BaseLoader, TemplateNotFound, \
    MemcachedBytecodeCache, FileSystemLoader as _Jinja2FileSystemLoader, \
    nodes
from jinja2.ext import Extension
from flask.helpers import _tojson_filter

from .config import ConfigAttribute
from .globals import _request_ctx_stack
from .signals import template_rendered
from .helpers import url_for, get_flashed_messages, _rst_to_html_filter, \
    make_crumbs


def _default_template_ctx_processor():
    """Default template context processor.  Injects `request`,
    `session` and `g`.
    """
    reqctx = _request_ctx_stack.top
    return dict(
        config=reqctx.app.config,
        request=reqctx.request,
        session=reqctx.session,
        g=reqctx.g,
        Decimal=Decimal,
        make_crumbs=make_crumbs,
    )


class TrytonTemplateLoader(BaseLoader):
    """
    Loaders are responsible for loading templates from a resource.
    In this case the tempalte is loaded from Tryton Database

    :param app: the application instance
    """
    model = 'nereid.template'

    def __init__(self, app):
        self.app = app

    def get_source(self, environment, template):
        """
        The environment provides a get_template method that calls 
        the loader’s load method to get the Template object. Hence,
        to override and implement a custom loading mechanism this
        method has to be sublassed.

        It’s passed the environment and template name and has to 
        return a tuple in the form (source, filename, uptodate)

        source - source of the template as unicode string/ASCII bytestring
        filename - None (as not loaded from filesystem)
        uptodate - A function to check if template has changed
        """
        template_obj = self.app.pool.get(self.model)
        source = template_obj.get_template_source(template)
        if source is None:
            raise TemplateNotFound(template)
        return source, None, lambda: False

    def list_templates(self):
        result = self.app.jinja_loader.list_templates()

        template_obj = self.app.pool.get(self.model)
        template_ids = template_obj.search([])
        for template in template_obj.browse(template_ids):
            result.append(template.name)

        return result


class FileSystemLoader(_Jinja2FileSystemLoader):
    """Loads templates from the file system."""

    def __init__(self, app):
        super(FileSystemLoader, self).__init__(
            app.config['TEMPLATE_SEARCH_PATH'])


class FragmentCacheExtension(Extension):
    # a set of names that trigger the extension.
    tags = set(['cache'])

    def __init__(self, environment):
        super(FragmentCacheExtension, self).__init__(environment)

        # add the defaults to the environment
        environment.extend(
            fragment_cache_prefix='',
            fragment_cache=None
            )

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = parser.stream.next().lineno

        # now we parse a single expression that is used as cache key.
        args = [parser.parse_expression()]

        # if there is a comma, the user provided a timeout.  If not use
        # None as second parameter.
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        # now we parse the body of the cache block up to `endcache` and
        # drop the needle (which would always be `endcache` in that case)
        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        return nodes.CallBlock(self.call_method('_cache_support', args),
                               [], [], body).set_lineno(lineno)

    def _cache_support(self, name, timeout, caller):
        """Helper callback."""
        key = self.environment.fragment_cache_prefix + name

        # try to load the block from the cache
        # if there is no fragment in the cache, render it and store
        # it in the cache.
        rv = self.environment.fragment_cache.get(key)
        if rv is not None:
            return rv
        rv = caller()
        self.environment.fragment_cache.add(key, rv, timeout)
        return rv


def _render(template, context, app):
    """Renders the template and fires the signal"""
    ret_val = template.render(context)
    template_rendered.send(app, template=template, context=context)
    return ret_val


def render_template(template_name, **context):
    """Renders a template from the template folder with the given
    context.

    :param template_name: the name of the template to be rendered
    :param context: the variables that should be available in the
                    context of the template.
    """
    ctx = _request_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.get_template(template_name),
                   context, ctx.app)


def render_template_string(source, **context):
    """Renders a template from the given template source string
    with the given context.

    :param template_name: the sourcecode of the template to be
                          rendered
    :param context: the variables that should be available in the
                    context of the template.
    """
    ctx = _request_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.from_string(source),
                   context, ctx.app)


class TemplateMixin(object):
    """Mixin class with attributes for the main 
    application to use"""

    #: Options that are passed directly to the Jinja2 environment.
    jinja_options = ImmutableDict(
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_', 
            FragmentCacheExtension]
    )
    template_loader_class = ConfigAttribute('TEMPLATE_LOADER_CLASS')
    context_proc_model = 'nereid.template.context_processor'

    def __init__(self, **config):
        #: A dictionary with list of functions that are called without argument
        #: to populate the template context.  The key of the dictionary is the
        #: name of the module this function is active for, `None` for all
        #: requests.  Each returns a dictionary that the template context is
        #: updated with.  
        self.template_context_processors = {
            None: [_default_template_ctx_processor]
        }

        #: The Jinja2 environment.  It is created from the
        #: :attr:`jinja_options`.
        self.jinja_env = self.create_jinja_environment()

        # Setup for fragmented caching
        self.jinja_env.fragment_cache = self.cache
        self.jinja_env.fragment_cache_prefix = self.cache_key_prefix + "-frag-"

        self.init_jinja_globals()

    def create_jinja_environment(self):
        """Creates the Jinja2 environment based on :attr:`jinja_options`
        and :meth:`select_jinja_autoescape`.
        """
        options = dict(self.jinja_options)
        if 'autoescape' not in options:
            options['autoescape'] = self.select_jinja_autoescape
        if self.cache and \
                self.cache_type=='werkzeug.contrib.cache.MemcachedCache':
            options['bytecode_cache'] = MemcachedBytecodeCache(self.cache)
        loader_class = import_string(self.template_loader_class)
        return Environment(
            loader=loader_class(self), 
            **options)

    def init_jinja_globals(self):
        """Called directly after the environment was created to inject
        some defaults (like `url_for`, `get_flashed_messages` and the
        `tojson` filter.
        """
        self.jinja_env.globals.update(
            url_for=url_for,
            get_flashed_messages=get_flashed_messages
        )
        self.jinja_env.filters['tojson'] = _tojson_filter
        self.jinja_env.filters['rst'] = _rst_to_html_filter

    def select_jinja_autoescape(self, filename):
        """Returns `True` if autoescaping should be active for the given
        template name.
        """
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))

    def add_ctx_processors_from_db(self):
        """Adds template context processors registers with the model
        nereid.template.context_processor"""
        with self.transaction:
            ctx_processor_obj = self.pool.get(self.context_proc_model)
            new_context_proc = ctx_processor_obj.get_processors()
            new_context_proc.setdefault(None, []).append(
                _default_template_ctx_processor)
            self.template_context_processors.update(new_context_proc)

    def update_template_context(self, context):
        """Update the template context with some commonly used variables.
        This injects request, session, config and g into the template
        context as well as everything template context processors want
        to inject.  Note that the original values in the context will 
        not be overriden if a context processor decides to return a 
        value with the same key.

        :param context: the context as a dictionary that is updated in place
                        to add extra variables.
        """
        funcs = self.template_context_processors[None]
        mod = _request_ctx_stack.top.request.module
        if mod is not None and mod in self.template_context_processors:
            funcs = chain(funcs, self.template_context_processors[mod])
        orig_ctx = context.copy()
        for func in funcs:
            context.update(func())
        # make sure the original values win.  This makes it possible to
        # easier add new variables in context processors without breaking
        # existing views.
        context.update(orig_ctx)

