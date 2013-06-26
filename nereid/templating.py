# -*- coding: utf-8 -*-
#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import os
import contextlib
from decimal import Decimal

from flask.templating import render_template
from jinja2 import BaseLoader, TemplateNotFound, nodes, Template, \
        ChoiceLoader, FileSystemLoader
from jinja2.ext import Extension
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders
import trytond.tools as tools
from trytond.transaction import Transaction

from .globals import request, current_app
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


class SiteNamePrefixLoader(FileSystemLoader):
    '''Loads templates from the file system but prefixes the template
    name with the name of the site.

    The loader takes the path to the templates as string, or if multiple
    locations are wanted a list of them which is then looked up in the
    given order:

    >>> loader = SiteNamePrefixLoader('/path/to/templates')
    >>> loader = SiteNamePrefixLoader(['/path/to/templates', '/other/path'])

    The templates are expected to be created on separate folders with
    the name of the website as defined when creating a nereid website.

    This loader can be used to emulate the default behavior of
    render_template in versions of Nereid prior to 2.8.0.4

    .. versionadded:: 2.8.0.4
    '''
    def get_source(self, environment, template):
        """
        Returns the source of the template after finding it in the local
        environment. This method adds the site name as a prefix to the
        template name as though the website name is a folder.
        """
        template = os.path.join(request.nereid_website.name, template)
        return super(SiteNamePrefixLoader, self).get_source(
            environment, template
        )


class ModuleTemplateLoader(ChoiceLoader):
    '''This loader works like the `ChoiceLoader` and loads templates from
    a filesystem path (optional) followed by the template folders in the
    tryton module path. The template folders are ordered by the same
    order in which Tryton arranges modules based on the dependencies.

    The optional keyword argument searchpath could be used to specify
    local folder which contains templates which may override the templates
    bundled into nereid modules.

    :param database_name: The name of the Tryton database. This is required
                          since the modules installed in a database is what
                          matters and not the modules in the site-packages
    :param searchpath: Optional filesystem path where templates that override
                       templates bundled with nereid are located.
    :param prefix_website_name: Flag to indicate if the website name needs to
                                be prefixed when looking up templates in the
                                given `searchpath`. This is not applicable to
                                templates loaded from packages as it would not
                                be possible to predict site names when writing
                                modules.
                                It is recommended not to use this feature, but
                                use the `NereidSiteNameLoader` directly to get
                                the same behavior. This would be deprecated in
                                future.

    .. versionadded:: 2.8.0.4
    '''
    def __init__(self, database_name, searchpath=None, prefix_website_name=False):
        self.database_name = database_name
        self.searchpath = searchpath
        self.prefix_website_name = prefix_website_name
        self._loaders = None

    @property
    def loaders(self):
        '''
        Lazy load the loaders
        '''
        if self._loaders is None:
            self._loaders = []

            if not Transaction().cursor:
                contextmanager = Transaction().start(self.database_name, 0)
            else:
                contextmanager = contextlib.nested(
                    Transaction().set_user(0),
                    Transaction().reset_context()
                )
            with contextmanager:
                cursor = Transaction().cursor
                cursor.execute("SELECT name FROM ir_module_module "
                    "WHERE state = 'installed'")
                installed_module_list = [name for (name,) in cursor.fetchall()]

            if self.searchpath is not None:
                # A path is specified from where templates have to be looked
                # up first
                if self.prefix_website_name:
                    # TODO: raise a deprecation warning
                    self._loaders.append(SiteNamePrefixLoader(self.searchpath))
                else:
                    self._loaders.append(FileSystemLoader(self.searchpath))

            # Look into the module graph and check if they have template
            # folders and if they do add them too
            from trytond.modules import create_graph, get_module_list, \
                    MODULES_PATH, EGG_MODULES

            packages = list(create_graph(get_module_list())[0])[::-1]
            for package in packages:
                if package.name not in installed_module_list:
                    # If the module is not installed in the current database
                    # then don't load the templates either to be consistent
                    # with Tryton's modularity
                    continue
                if package.name in EGG_MODULES:
                    # trytond.tools has a good helper which allows resources to
                    # be loaded from the installed site packages. Just use it
                    # to load the tryton.cfg file which is guaranteed to exist
                    # and from it lookup the directory. From here, its just
                    # another searchpath for the loader.
                    f = tools.file_open(
                        os.path.join(package.name, 'tryton.cfg')
                    )
                    template_dir = os.path.join(
                        os.path.dirname(f.name), 'templates'
                    )
                else:
                    template_dir = os.path.join(
                        MODULES_PATH, package.name, 'templates'
                    )
                if os.path.isdir(template_dir):
                    # Add to FS Loader only if the folder exists
                    self._loaders.append(FileSystemLoader(template_dir))

        return self._loaders


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
        if isinstance(text_template, Template):
            text = text_template.render(**context)
        else:
            text = render_template(text_template, **context)
        text_part = MIMEText(text.encode("utf-8"), 'plain', _charset="UTF-8")
        msg.attach(text_part)
    if html_template:
        if isinstance(html_template, Template):
            html = html_template.render(**context)
        else:
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
