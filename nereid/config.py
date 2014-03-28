# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import imp

from flask.config import ConfigAttribute, Config as ConfigBase  # noqa


class Config(ConfigBase):
    "Configuration without the root_path"

    def __init__(self, defaults=None):
        dict.__init__(self, defaults or {})

    def from_pyfile(self, filename):
        """
        Updates the values in the config from a Python file.  This function
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
