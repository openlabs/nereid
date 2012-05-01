# -*- coding: UTF-8 -*-
'''
    nereid.session

    Implements cookie based sessions

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
from warnings import warn
warn(DeprecationWarning("Use nereid.sessions instead"))

from .sessions import Session, NullSession, MemcachedSessionStore, \
    NereidSessionInterface
