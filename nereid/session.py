# -*- coding: UTF-8 -*-
'''
    nereid.session

    Implements cookie based sessions

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
from datetime import datetime

from flask.session import _NullSession
from werkzeug.contrib.sessions import Session as SessionBase, SessionStore
from werkzeug.contrib.sessions import FilesystemSessionStore
from werkzeug.utils import import_string

from .config import ConfigAttribute
from .globals import current_app, cache


class Session(SessionBase):
    """Expands the session with support for switching between permanent
    and non-permanent sessions.
    """

    def _get_permanent(self):
        return self.get('_permanent', False)

    def _set_permanent(self, value):
        self['_permanent'] = bool(value)

    permanent = property(_get_permanent, _set_permanent)
    del _get_permanent, _set_permanent


class MemcachedSessionStore(SessionStore):
    """Session store that stores session on memcached

    :param session_class: The session class to use.  Defaults to
                          :class:`Session`.
    """
    def __init__(self, session_class=Session):
        SessionStore.__init__(self, session_class)

    def save(self, session):
        success = cache.set(session.sid, dict(session))

    def delete(self, session):
        cache.delete(session.sid)

    def get(self, sid):
        if not self.is_valid_key(sid):
            return self.new()
        session_data = cache.get(sid)
        if session_data is None:
            session_data = {}
        return self.session_class(session_data, sid, False)

    def list(self):
        """Lists all sessions in the store
        """
        raise Exception("Not implemented yet")


class SessionMixin(object):
    """Session Management Class"""

    #: The session class to use.  Defaults to
    #: :class:`werkzeug.contrib.sessions.Session`.
    session_class = ConfigAttribute('SESSION_CLASS')

    #: The class to generate the session store
    #: Defaults to :class:`FilesystemSessionStore`
    session_store_class = ConfigAttribute('SESSION_STORE_CLASS')

    #: The secure cookie uses this for the name of the session cookie.
    #: This attribute can also be configured from the config with the
    #: `SESSION_COOKIE_NAME` configuration key.  Defaults to ``'session'``
    session_cookie_name = ConfigAttribute('SESSION_COOKIE_NAME')

    #: A :class:`~datetime.timedelta` which is used to set the expiration
    #: date of a permanent session.  The default is 31 days which makes a
    #: permanent session survive for roughly one month.
    #:
    #: This attribute can also be configured from the config with the
    #: `PERMANENT_SESSION_LIFETIME` configuration key.  Defaults to
    #: ``timedelta(days=31)``
    permanent_session_lifetime = ConfigAttribute('PERMANENT_SESSION_LIFETIME')

    #: Path where the session files can be stored. This is only for
    #: Filesystem Cache. The FilesystemCache is a simple implementation
    #: and does not scale for production use.
    session_store_path = ConfigAttribute('SESSION_STORE_PATH')

    def __init__(self, **config):
        session_store_class = import_string(self.session_store_class)
        if session_store_class == FilesystemSessionStore:
            self.session_store = FilesystemSessionStore(
                self.session_store_path, session_class=self.session_class)
        elif session_store_class == MemcachedSessionStore:
            self.session_store =   MemcachedSessionStore(
                session_class=self.session_class)

    def open_session(self, request):
        """Creates or opens a new session.

        :param request: an instance of :attr:`request_class`.
        """
        sid = request.cookies.get(self.session_cookie_name, None)
        if sid is None:
            return self.session_store.new()
        else:
            return self.session_store.get(sid)

    def save_session(self, session, response):
        """Saves the session if it needs updates.  For the default
        implementation, check :meth:`open_session`.

        :param session: the session to be saved
        :param response: an instance of :attr:`response_class`
        """
        self.session_store.save(session)
        expires = domain = None
        if session.permanent:
            expires = datetime.utcnow() + self.permanent_session_lifetime
        if self.config['SERVER_NAME'] is not None:
            domain = '.' + self.config['SERVER_NAME']
        response.set_cookie(self.session_cookie_name, session.sid, 
            expires=expires, httponly=True, domain=domain)
