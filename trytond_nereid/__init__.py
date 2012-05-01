# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
'''
    trytond_nereid.file

Tryton module to support Nereid

:copyright: (c) 2010 by Sharoon Thomas.
:copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Limited.
:license: GPLv3, see LICENSE for more details
'''

from .party import Address, NereidUser
from .routing import *
from .template import Template
from .static_file import NereidStaticFolder, NereidStaticFile
from .currency import Currency
