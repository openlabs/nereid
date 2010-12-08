# -*- coding: UTF-8 -*-
'''
    nereid.wrappers

    Implements the WSGI wrappers

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''

from flask.wrappers import Request as RequestBase, Response as ResponseBase


class Request(RequestBase):
    pass


class Response(ResponseBase):
    pass
