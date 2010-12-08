# -*- coding: UTF-8 -*-
'''
    nereid

A microframework based on Flask, Werkzeug and powered by the 
Tryton ERP.

It replicates the Flask API for most of the system

:copyright: (c) 2010 by Sharoon Thomas.
:license: BSD, see LICENSE for more details
'''

# utilities we import from Werkzeug and Jinja2 that are unused
# in the module but are exported as public interface.
from werkzeug import abort, redirect
from jinja2 import Markup, escape

from .globals import current_app, g, request, \
    session, _request_ctx_stack, transaction

from .application import Nereid, Request, Response
from .session import Session
