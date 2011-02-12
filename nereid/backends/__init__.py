# -*- coding: UTF-8 -*-
'''
    nereid.backend

    Backend collection for nereid

    :copyright: (c) 2010-2011 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''

def _get_module(config):
    """Return the corresponding module

    >>> config = {'BACKEND': 'tryton', 'BACKEND_VERSION': '1.8'}
    """
    module = None
    if config['BACKEND'] == 'tryton':
        if config['BACKEND_VERSION'] == '1.8':
            from . import tryton_1_8 as module
        elif config['BACKEND_VERSION'] == '1.6':
            from . import tryton_1_8 as module

    elif config['BACKEND'] == 'openerp':
        if config['BACKEND_VERSION'] in ('5', '6'):
            from . import openerp as module

    if module is None:
        raise Exception("Backend %s Ver.%s is not valid" % (
            config['BACKEND'], config['BACKEND_VERSION']))

    return module

def get_connection(config):
    """Return the connection depending on config

    >>> get_connection({'BACKEND': 'openerp', 'BACKEND_VERSION': '5'})
    <class 'nereid.backend.openerp.Connection'>
    >>> get_connection({'BACKEND': 'tryton', 'BACKEND_VERSION': '1.8'})
    <class 'nereid.backend.tryton_1_8.Connection'>

    """
    module = _get_module(config)
    return module.Connection

def get_transaction(config):
    "Return the transaction depending on config"
    module = _get_module(config)
    return module.Transaction

def get_root_user(config):
    "Return the root user depending on config"
    module = _get_module(config)
    return module.ROOT_USER

def get_paginator(config):
    "Return the Paginator object depending on config"
    module = _get_module(config)
    return module.Paginator


class BackendMixin(object):
    """
    A special mixin class for the applciation to enjoy the
    above methods without any configuration handling
    """

    @property
    def connection(self):
        "Connection to Backend"
        return get_connection(self.config)

    @property
    def transaction_class(self):
        "Backend Transaction manager class"
        return get_transaction(self.config)

    @property
    def root_user(self):
        "Backend Root User"
        return get_root_user(self.config)

    @property
    def paginator(self):
        "Pagination class"
        return get_paginator(self.config)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
