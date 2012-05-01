# -*- coding: UTF-8 -*-
'''
    nereid.config

    Configuration

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
import imp

from flask.config import ConfigAttribute, Config as ConfigBase


class Config(ConfigBase):
    "Configuration without the root_path"

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or { })

    def from_pyfile(self, filename):
        """Updates the values in the config from a Python file.  This function
        behaves as if the file was imported as module with the
        :meth:`from_object` function.

        :param filename: the filename of the config.  This can either be an
                         absolute filename or a filename relative to the
                         root path.
        """
        d = imp.new_module('config')
        d.__file__ = filename
        try:
            execfile(filename, d.__dict__)
        except IOError, e:
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        self.from_object(d)

