# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from functools import wraps
from hashlib import md5
import inspect
from warnings import warn
warn(DeprecationWarning("This API will be deprecated"))

from flask.globals import current_app


class Cache(object):
    """
    Implements a Cache with helper utils

    This is implemented using __slots__ based optimisation
    and reimplements most arguments already in the application.
    However, this will increase performance as cache related
    operations will then not depend on a dictionary lookup, which
    is one of the most expensive python operations.

    :param app: Instance of application. Values for cache are
                fetched from there
    """
    __slots__ = tuple()

    def add(self, key, value, timeout=None):
        "Proxy function for internal cache object."
        return current_app.cache.add(key, value, timeout)

    def clear(self):
        "Proxy function for internal cache object."
        return current_app.cache.clear()

    def dec(self, key, delta=1):
        "Proxy function for internal cache object."
        return current_app.cache.dec(key, delta)

    def delete(self, key):
        "Proxy function for internal cache object."
        return current_app.cache.delete(key)

    def delete_many(self, *keys):
        "Proxy function for internal cache object."
        return current_app.cache.delete_many(*keys)

    def get(self, key):
        "Proxy function for internal cache object."
        return current_app.cache.get(key)

    def get_dict(self, *keys):
        "Proxy function for internal cache object."
        return current_app.cache.get_dict(*keys)

    def get_many(self, *keys):
        "Proxy function for internal cache object."
        return current_app.cache.get_many(*keys)

    def inc(self, key, delta=1):
        "Proxy function for internal cache object."
        return current_app.cache.inc(key, delta)

    def set(self, key, value, timeout=None):
        "Proxy function for internal cache object."
        return current_app.cache.set(key, value, timeout)

    def set_many(self, mapping, timeout=None):
        "Proxy function for internal cache object."
        return current_app.cache.set_many(mapping, timeout)

    def cache(self, key, timeout=None, unless=None):
        """
        Decorator to use as caching function

        :copyright: (c) 2010 by Thadeus Burgess.

        :param timeout: Time in seconds to retain cached value
        :param key_prefix: Key to use for cache.
        :param unless: Callable for truth testing. If provided, the
                       callable is called with no arguments and if true,
                       caching operation will be cancelled.
        """
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):
                if callable(unless) and unless() is True:
                    return function(*args, **kwargs)

                rv = current_app.cache.get(key)

                if rv is None:
                    rv = function(*args, **kwargs)
                    current_app.cache.set(key, rv, timeout)
                return rv
            return wrapper
        return decorator

    def memoize(self, key, timeout=None, unless=None):
        """
        Decorator to use as caching function but also evaluates
        the arguments

        :copyright: (c) 2010 by Thadeus Burgess.

        :param timeout: Time in seconds to retain cached value
        :param key_prefix: Key to use for cache.
        :param unless: Callable for truth testing. If provided, the
                       callable is called with no arguments and if true,
                       caching operation will be cancelled
        """
        def decorator(function):
            arg_names = inspect.getargspec(function)[0]

            @wraps(function)
            def wrapper(*args, **kwargs):
                if callable(unless) and unless() is True:
                    return function(*args, **kwargs)

                kwargs_origin = kwargs.copy()
                kwargs.update(dict(zip(arg_names, args)))
                kwargs = kwargs.items()
                kwargs.sort()

                hash = md5()
                hash.update(key + repr(kwargs))
                cache_key = hash.hexdigest()

                rv = current_app.cache.get(cache_key)

                if rv is None:
                    rv = function(*args, **kwargs_origin)
                    current_app.cache.set(cache_key, rv, timeout)
                return rv
            return wrapper
        return decorator

    def memoize_method(self, key, timeout=None, unless=None):
        """
        Decorator to use as caching function but also evaluates
        the arguments

        :copyright: (c) 2010 by Thadeus Burgess.

        :param timeout: Time in seconds to retain cached value
        :param key_prefix: Key to use for cache.
        :param unless: Callable for truth testing. If provided, the
                       callable is called with no arguments and if true,
                       caching operation will be cancelled
        """
        def decorator(function):
            arg_names = inspect.getargspec(function)[0]

            @wraps(function)
            def wrapper(*args, **kwargs):
                if callable(unless) and unless() is True:
                    return function(*args, **kwargs)

                kwargs_origin = kwargs.copy()
                kwargs.update(dict(zip(arg_names, args)))
                kwargs.pop('self')
                kwargs = kwargs.items()
                kwargs.sort()

                hash = md5()
                hash.update(key + repr(args[1:]) + repr(kwargs))
                cache_key = hash.hexdigest()

                rv = current_app.cache.get(cache_key)

                if rv is None:
                    rv = function(*args, **kwargs_origin)
                    current_app.cache.set(cache_key, rv, timeout)
                return rv
            return wrapper
        return decorator
