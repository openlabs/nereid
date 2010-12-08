# -*- coding: UTF-8 -*-
'''
    nereid.session

    Implements cookie based sessions

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''

from flask.session import Session, _NullSession

from .config import ConfigAttribute


class SessionMixin(object):
    """Session Management Class"""

    #: If a secret key is set, cryptographic components can use this to
    #: sign cookies and other things.  Set this to a complex random value
    #: when you want to use the secure cookie for instance.
    #:
    #: This attribute can also be configured from the config with the
    #: `SECRET_KEY` configuration key.  Defaults to `None`.
    secret_key = ConfigAttribute('SECRET_KEY')

    #: The secure cookie uses this for the name of the session cookie.
    #:
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

    def __init__(self, **config):
        pass

    def open_session(self, request):
        """Creates or opens a new session.  Default implementation stores all
        session data in a signed cookie.  This requires that the
        :attr:`secret_key` is set.

        :param request: an instance of :attr:`request_class`.
        """
        key = self.secret_key
        if key is not None:
            return Session.load_cookie(
                request, self.session_cookie_name, secret_key=key)

    def save_session(self, session, response):
        """Saves the session if it needs updates.  For the default
        implementation, check :meth:`open_session`.

        :param session: the session to be saved (a
                        :class:`~werkzeug.contrib.securecookie.SecureCookie`
                        object)
        :param response: an instance of :attr:`response_class`
        """
        expires = domain = None
        if session.permanent:
            expires = datetime.utcnow() + self.permanent_session_lifetime
        if self.config['SERVER_NAME'] is not None:
            domain = '.' + self.config['SERVER_NAME']
        session.save_cookie(response, self.session_cookie_name,
                            expires=expires, httponly=True, domain=domain)

