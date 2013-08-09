# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool

from .party import Address, Party, ContactMechanism, NereidUser, Permission, \
    UserPermission
from .routing import URLMap, WebSite, URLRule, URLRuleDefaults, \
    WebsiteCountry, WebsiteCurrency
from .static_file import NereidStaticFolder, NereidStaticFile
from .currency import Currency, Language
from .template import ContextProcessors


def register():
    Pool.register(
        Address,
        Party,
        ContactMechanism,
        NereidUser,
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
        Language,
        Currency,
        ContextProcessors,
        module='nereid', type_='model'
    )
