# -*- coding: utf-8 -*-
"""
    nereid.cache

    Adds cache support to a nereid application

    :copyright: © 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from functools import wraps
from hashlib import md5
import inspect

from werkzeug import import_string

from .globals import cache
from .config import ConfigAttribute


class CacheMixin(object):
    """This mixin allows caching to be used in compliance with the
    werkzeug cache backends
    """
    #: The default timeout to use if the timeout is not explicitly
    #: specified in the set or set many argument
    cache_default_timeout = ConfigAttribute('CACHE_DEFAULT_TIMEOUT')

    #: the maximum number of items the cache stores before it starts 
    #: deleting some items.
    #: Applies for: SimpleCache, FileSystemCache
    cache_threshold = ConfigAttribute('CACHE_THRESHOLD')

    #: a prefix that is added before all keys. This makes it possible 
    #: to use the same memcached server for different applications.
    #: Applies for: MecachedCache, GAEMemcachedCache
    #: If key_prefix is none the value of site is used as key
    cache_key_prefix = ConfigAttribute('CACHE_KEY_PREFIX')

    #: a list or tuple of server addresses or alternatively a 
    #: `memcache.Client` or a compatible client.
    cache_memcached_servers = ConfigAttribute('CACHE_MEMCACHED_SERVERS')

    #: The directory where cache files are stored if FileSystemCache is used
    cache_dir = ConfigAttribute('CACHE_DIR') 

    #: The type of cache to use. The type must be a full specification of
    #: the module so that an import can be made. Examples for werkzeug 
    #: backends are given below
    #:
    #:  NullCache - werkzeug.contrib.cache.NullCache (default)
    #:  SimpleCache - werkzeug.contrib.cache.SimpleCache
    #:  MemcachedCache - werkzeug.contrib.cache.MemcachedCache
    #:  GAEMemcachedCache -  werkzeug.contrib.cache.GAEMemcachedCache
    #:  FileSystemCache - werkzeug.contrib.cache.FileSystemCache
    cache_type = ConfigAttribute('CACHE_TYPE')

    #: If a custom cache backend unknown to Nereid is used, then
    #: the arguments that are needed for the initialisation
    #: of the cache could be passed here as a `dict`
    cache_init_kwargs = ConfigAttribute('CACHE_INIT_KWARGS')

    def __init__(self, **kwargs):
        if self.cache_key_prefix is None:
            self.cache_key_prefix = self.site

        BackendClass = import_string(self.cache_type)

        if self.cache_type == 'werkzeug.contrib.cache.NullCache':
            self.cache = BackendClass(self.cache_default_timeout)
        elif self.cache_type == 'werkzeug.contrib.cache.SimpleCache':
            self.cache = BackendClass(
                self.cache_threshold, self.cache_default_timeout)
        elif self.cache_type == 'werkzeug.contrib.cache.MemcachedCache':
            self.cache = BackendClass(
                self.cache_memcached_servers,
                self.cache_default_timeout,
                self.cache_key_prefix)
        elif self.cache_type == 'werkzeug.contrib.cache.GAEMemcachedCache':
            self.cache = BackendClass(
                self.cache_default_timeout,
                self.cache_key_prefix)
        elif self.cache_type == 'werkzeug.contrib.cache.FileSystemCache':
            self.cache = BackendClass(
                self.cache_dir,
                self.cache_threshold,
                self.cache_default_timeout)
        else:
            self.cache = BackendClass(**self.cache_init_kwargs)


class Cache(object):
    """Implements a Cache with helper utils

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
        return cache.add(key, value, timeout)

    def clear(self):
        "Proxy function for internal cache object."
        return cache.clear()

    def dec(self, key, delta=1):
        "Proxy function for internal cache object."
        return cache.dec(key, delta)

    def delete(self, key):
        "Proxy function for internal cache object."
        return cache.delete(key)

    def delete_many(self, *keys):
        "Proxy function for internal cache object."
        return cache.delete_many(*keys)

    def get(self, key):
        "Proxy function for internal cache object."
        return cache.get(key)

    def get_dict(self, *keys):
        "Proxy function for internal cache object."
        return cache.get_dict(*keys)

    def get_many(self, *keys):
        "Proxy function for internal cache object."
        return cache.get_many(*keys)

    def inc(self, key, delta=1):
        "Proxy function for internal cache object."
        return cache.inc(key, delta)

    def set(self, key, value, timeout=None):
        "Proxy function for internal cache object."
        return cache.set(key, value, timeout)

    def set_many(self, mapping, timeout=None):
        "Proxy function for internal cache object."
        return cache.set_many(mapping, timeout)

    def cache(self, key, timeout=None, unless=None):
        """Decorator to use as caching function

        :copyright: (c) 2010 by Thadeus Burgess.

        :param timeout: Time in seconds to retain cached value
        :param key_prefix: Key to use for cache. 
        :param unless: Callable for truth testing. If provided, the 
            callable is called with no arguments and if true, caching
            operation will be cancelled
        """
        def decorator(function):
            @wraps(function)
            def wrapper(*args, **kwargs):
                if callable(unless) and unless() is True:
                    return function(*args, **kwargs)

                rv = cache.get(key)

                if rv is None:
                    rv = function(*args, **kwargs)
                    cache.set(key, rv, timeout)
                return rv
            return wrapper
        return decorator

    def memoize(self, key, timeout=None, unless=None):
        """Decorator to use as caching function but also evaluates
        the arguments

        :copyright: (c) 2010 by Thadeus Burgess.

        :param timeout: Time in seconds to retain cached value
        :param key_prefix: Key to use for cache. 
        :param unless: Callable for truth testing. If provided, the 
            callable is called with no arguments and if true, caching
            operation will be cancelled
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

                rv = cache.get(cache_key)

                if rv is None:
                    rv = function(*args, **kwargs_origin)
                    cache.set(cache_key, rv, timeout)
                return rv
            return wrapper
        return decorator

    def memoize_method(self, key, timeout=None, unless=None):
        """Decorator to use as caching function but also evaluates
        the arguments

        :copyright: (c) 2010 by Thadeus Burgess.

        :param timeout: Time in seconds to retain cached value
        :param key_prefix: Key to use for cache.
        :param unless: Callable for truth testing. If provided, the 
            callable is called with no arguments and if true, caching
            operation will be cancelled
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

                rv = cache.get(cache_key)

                if rv is None:
                    rv = function(*args, **kwargs_origin)
                    cache.set(cache_key, rv, timeout)
                return rv
            return wrapper
        return decorator


if __name__ == '__main__':
    import doctest
    doctest.testmod()
