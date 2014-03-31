# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import warnings

from werkzeug._internal import _missing
from flask.wrappers import Request as RequestBase, Response as ResponseBase
from flask.ext.login import current_user

from .globals import current_app, request
from .signals import transaction_stop


class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dictcache__` in order for this property to
    work.

    If the transaction has changed then the cache is invalidated

    Based on werkzeug.utils.cached_property
    """

    # implementation detail: this property is implemented as non-data
    # descriptor.  non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dictcache__.
    # this allows us to completely get rid of the access function call
    # overhead.  If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dictcache__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dictcache__[self.__name__] = value
        return value


class Request(RequestBase):
    "Request Object"

    def __init__(self, *args, **kwargs):
        super(Request, self).__init__(*args, **kwargs)
        self.__dictcache__ = {}

    @staticmethod
    @transaction_stop.connect
    def clear_dictcache(app):
        """
        Clears the dictcache which stored the cached values of the records
        below.
        """
        request.__dictcache__ = {}

    @cached_property
    def nereid_website(self):
        """Fetch the Browse Record of current website."""
        if self.url_rule is None:
            return None
        Website = current_app.pool.get('nereid.website')
        return Website.get_from_host(self.host)

    @cached_property
    def nereid_user(self):
        """Fetch the browse record of current user or None."""
        warnings.warn(
            "request.nereid_user will be deprecated. "
            "Use `nereid.current_user` proxy instead.",
            DeprecationWarning, stacklevel=2
        )
        return current_user

    @cached_property
    def nereid_currency(self):
        """
        Return a browse record for the currency.
        """
        return self.nereid_locale.currency

    @cached_property
    def nereid_locale(self):
        """
        Returns the active record of the current locale.
        The locale could either be from the URL if the locale was specified
        in the URL, or the default locale from the website.
        """
        if self.view_args and 'locale' in self.view_args:
            for locale in self.nereid_website.locales:
                if locale.code == self.view_args['locale']:
                    return locale

        # Return the default locale
        return self.nereid_website.default_locale

    @cached_property
    def nereid_language(self):
        """
        Return a active record for the language.
        """
        return self.nereid_locale.language

    @cached_property
    def is_guest_user(self):
        """Return true if the user is guest."""
        warnings.warn(
            "request.is_guest_user will be deprecated. "
            "Use `nereid.current_user` proxy and "
            "current_user.is_anonymous instead",
            DeprecationWarning, stacklevel=2
        )
        return current_user.is_anonymous()

    @property
    def is_json(self):
        """Indicates if this request is JSON or not.  By default a request
        is considered to include JSON data if the mimetype is
        ``application/json`` or ``application/*+json``.

        This feature is forward ported from flask 0.11. When flask is released
        this will be removed from nereid code

        .. versionadded:: 3.0.4.0
        """
        mt = self.mimetype
        if mt == 'application/json':
            return True
        if mt.startswith('application/') and mt.endswith('+json'):
            return True
        return False


class Response(ResponseBase):
    pass
