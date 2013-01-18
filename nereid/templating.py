# -*- coding: UTF-8 -*-
'''
    nereid.templating

    Implements the Jinja2 bridge

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :copyright: (c) 2010 by Armin Ronacher.
    :license: GPLv3, see LICENSE for more details
'''
from decimal import Decimal

from flask.templating import render_template as flask_render_template
from jinja2 import BaseLoader, TemplateNotFound, nodes
from jinja2.ext import Extension
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders

from .globals import request
from .helpers import _rst_to_html_filter, make_crumbs


def nereid_default_template_ctx_processor():
    """Add Decimal and make_crumbs to template context"""
    return dict(
        Decimal=Decimal,
        make_crumbs=make_crumbs,
    )


NEREID_TEMPLATE_FILTERS = dict(
    rst = _rst_to_html_filter,
)

def render_template(template_name, _prefix_website=True, **context):
    """Renders a template and by default adds the current website
    name as a prefix to the template name thereby allowing automatic
    name conversions from nereid base template to application specific
    templates
    """
    if _prefix_website:
        template_name = '%s/%s' % (
            request.nereid_website.name, template_name
        )
    return flask_render_template(template_name, **context)


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


def render_email(from_email, to, subject,
        text_template=None, html_template=None, cc=None, attachments=None,
        **context):
    """Read the templates for email messages, format them, construct
    the email from them and return the corresponding email message
    object.

    :param from_email: Email From
    :param to: Email IDs of direct recepients
    :param subject: Email subject
    :param text_template: <Text email template path>
    :param html_template: <HTML email template path>
    :param cc: Email IDs of Cc recepients
    :param attachments: A dict of filename:string as key value pair
        [preferable file buffer streams]
    :param context: Context to be sent to template rendering

    :return: Email multipart instance or Text/HTML part
    """
    if not (text_template or html_template):
        raise Exception("Atleast HTML or TEXT template is required")
        
    # Create the body of the message (a plain-text and an HTML version).
    # text is your plain-text email
    # html is your html version of the email
    # if the reciever is able to view html emails then only the html
    # email will be displayed
    if attachments:
        msg = MIMEMultipart('mixed')
    else:
        msg = MIMEMultipart('alternative')
    if text_template:
        text = render_template(text_template, **context)
        text_part = MIMEText(text.encode("utf-8"), 'plain', _charset="UTF-8")
        msg.attach(text_part)
    if html_template:
        html = render_template(html_template, **context)
        html_part = MIMEText(html.encode("utf-8"), 'html', _charset="UTF-8")
        msg.attach(html_part)
        
    if text_template and not (html_template or attachments):
        msg = text_part
    elif html_template and not (text_template or attachments):
        msg = html_part

    if attachments:
        for filename, content in attachments.items():
            part = MIMEBase('application', "octet-stream")
            part.set_payload(content)
            Encoders.encode_base64(part)
            #XXX: Filename might have to be encoded with utf-8,
            # i.e., part's encoding or with email's encoding
            part.add_header(
                'Content-Disposition', 'attachment; filename="%s"' % filename
            )
            msg.attach(part)

    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to
    msg['Cc'] = cc or ''

    return msg
