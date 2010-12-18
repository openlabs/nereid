# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
'''
    trytond_nereid.file

Tryton module to support Nereid

:copyright: (c) 2010 by Sharoon Thomas.
:license: BSD, see LICENSE for more details
'''

from .routing import *
#from auth import User, Address
from .template import Template
from .static_file import NereidStaticFolder, NereidStaticFile
from .party import Address
