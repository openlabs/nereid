# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool

from .party import Address, Party, ContactMechanism, NereidUser, Permission, \
    UserPermission
from .routing import URLMap, WebSite, WebSiteLocale, URLRule, URLRuleDefaults, \
    WebsiteCountry, WebsiteCurrency, WebsiteWebsiteLocale
from .static_file import NereidStaticFolder, NereidStaticFile
from .currency import Currency
from .template import ContextProcessors
from .configuration import NereidConfigStart, NereidConfig
from .i18n import Translation, TranslationSet


def register():
    Pool.register(
        Address,
        Party,
        ContactMechanism,
        NereidUser,
        Permission,
        UserPermission,
        URLMap,
        WebSiteLocale,
        WebSite,
        URLRule,
        URLRuleDefaults,
        WebsiteCountry,
        WebsiteCurrency,
        WebsiteWebsiteLocale,
        NereidStaticFolder,
        NereidStaticFile,
        Currency,
        ContextProcessors,
        NereidConfigStart,
        Translation,
        module='nereid', type_='model'
    )
    Pool.register(
        NereidConfig,
        TranslationSet,
        module='nereid', type_='wizard'
    )
