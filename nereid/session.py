# -*- coding: UTF-8 -*-
'''
    nereid.session

    Implements cookie based sessions

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
from datetime import datetime

from flask.sessions import SessionInterface
from werkzeug.contrib.sessions import Session as SessionBase, SessionStore

from .globals import cache


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

    #: some session backends can tell you if a session is new, but that is
    #: not necessarily guaranteed.  Use with caution.  The default mixin
    #: implementation just hardcodes `False` in.
    new = False

    #: for some backends this will always be `True`, but some backends will
    #: default this to false and detect changes in the dictionary for as
    #: long as changes do not happen on mutable structures in the session.
    #: The default mixin implementation just hardcodes `True` in.
    modified = True


class NullSession(Session):
    """Class used to generate nicer error messages if sessions are not
    available.  Will still allow read-only access to the empty session
    but fail on setting.
    """

    def _fail(self, *args, **kwargs):
        raise RuntimeError('the session is unavailable because no secret '
                           'key was set.  Set the secret_key on the '
                           'application to something unique and secret.')
    __setitem__ = __delitem__ = clear = pop = popitem = \
        update = setdefault = _fail
    del _fail


class MemcachedSessionStore(SessionStore):
    """Session store that stores session on memcached

    :param session_class: The session class to use.  Defaults to
                          :class:`Session`.
    """
    def __init__(self, session_class=Session):
        SessionStore.__init__(self, session_class)

    def save(self, session):
        success = cache.set(session.sid, dict(session), 30 * 24 * 60 * 60)

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


class NereidSessionInterface(SessionInterface):
    """Session Management Class"""

    session_store = MemcachedSessionStore()
    null_session_class = NullSession

    def open_session(self, app, request):
        """Creates or opens a new session.

        :param request: an instance of :attr:`request_class`.
        """
        sid = request.cookies.get(app.session_cookie_name, None)
        if sid:
            return self.session_store.get(sid)
        else:
            return self.session_store.new()

    def save_session(self, app, session, response):
        """Saves the session if it needs updates.  For the default
        implementation, check :meth:`open_session`.

        :param session: the session to be saved
        :param response: an instance of :attr:`response_class`
        """
        if session.should_save:
            self.session_store.save(session)
            expires = domain = None
            if session.permanent:
                expires = datetime.utcnow() + app.permanent_session_lifetime
            if app.config['SERVER_NAME'] is not None:
                domain = '.' + app.config['SERVER_NAME']
            response.set_cookie(app.session_cookie_name, session.sid, 
                expires=expires, httponly=True, domain=domain)
