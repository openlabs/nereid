# -*- coding: UTF-8 -*-
'''
    nereid.templating

    Implements the Jinja2 bridge

    :copyright: (c) 2010 by Sharoon Thomas.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details
'''
from itertools import chain

from werkzeug import ImmutableDict
from jinja2 import Environment, BaseLoader, TemplateNotFound
from flask.helpers import _tojson_filter

from .globals import _request_ctx_stack
from .signals import template_rendered
from .helpers import url_for, get_flashed_messages


def _default_template_ctx_processor():
    """Default template context processor.  Injects `request`,
    `session` and `g`.
    """
    reqctx = _request_ctx_stack.top
    return dict(
        config=reqctx.app.config,
        request=reqctx.request,
        session=reqctx.session,
        g=reqctx.g
    )


class TrytonTemplateLoader(BaseLoader):
    """
    Loaders are responsible for loading templates from a resource.
    In this case the tempalte is loaded from Tryton Database

    :param app: the application instance
    """
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
        template_obj = self.app.pool.get('nereid.template')
        source = template_obj.get_template_source(template)
        if source is None:
            raise TemplateNotFound(template)
        return source, None, lambda: False

    def list_templates(self):
        result = self.app.jinja_loader.list_templates()

        template_obj = self.app.pool.get('nereid.template')
        template_ids = template_obj.search([])
        for template in template_obj.browse(template_ids):
            result.append(template.name)

        return result


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
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_']
    )

    def __init__(self, **config):
        #: A dictionary with list of functions that are called without argument
        #: to populate the template context.  The key of the dictionary is the
        #: name of the module this function is active for, `None` for all
        #: requests.  Each returns a dictionary that the template context is
        #: updated with.  To register a function here, use the
        #: :meth:`context_processor` decorator.
        self.template_context_processors = {
            None: [_default_template_ctx_processor]
        }

        #: The Jinja2 environment.  It is created from the
        #: :attr:`jinja_options`.
        self.jinja_env = self.create_jinja_environment()
        self.init_jinja_globals()


    def create_jinja_environment(self):
        """Creates the Jinja2 environment based on :attr:`jinja_options`
        and :meth:`select_jinja_autoescape`.
        """
        options = dict(self.jinja_options)
        if 'autoescape' not in options:
            options['autoescape'] = self.select_jinja_autoescape
        return Environment(loader=TrytonTemplateLoader(self), **options)

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

    def select_jinja_autoescape(self, filename):
        """Returns `True` if autoescaping should be active for the given
        template name.
        """
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))

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

