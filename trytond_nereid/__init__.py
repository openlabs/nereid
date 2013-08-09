# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool

from .party import *
from .routing import *
from .static_file import *
from .currency import *
from .template import *


def register():
    Pool.register(
        Address,
        Party,
        NereidUser,
        ContactMechanism,
        Permission,
        UserPermission,
        URLMap,
        WebSite,
        URLRule,
        URLRuleDefaults,
        WebsiteCountry,
        WebsiteCurrency,
        NereidStaticFolder,
        NereidStaticFile,
        Currency,
        ContextProcessors,
        Language,
        module='nereid', type_='model'
    )
