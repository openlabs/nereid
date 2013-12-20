#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from werkzeug import redirect, abort
from werkzeug._internal import _missing
from flask.wrappers import Request as RequestBase, Response as ResponseBase
from .helpers import url_for
from .globals import current_app, session, request
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
        if self.url_rule.host is None:
            return None
        Website = current_app.pool.get('nereid.website')
        return Website.search([('name', '=', self.url_rule.host)])[0]

    @cached_property
    def nereid_user(self):
        """Fetch the browse record of current user or None."""
        NereidUser = current_app.pool.get('nereid.user')
        if 'user' not in session:
            return NereidUser(self.nereid_website.guest_user.id)

        try:
            nereid_user, = NereidUser.search([('id', '=', session['user'])])
        except ValueError:
            session.pop('user')
            abort(redirect(url_for('nereid.website.login')))
        else:
            return nereid_user

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
        return ('user' not in session)


class Response(ResponseBase):
    pass
