# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool

from .party import Address, Party, ContactMechanism
from .user import NereidUser, Permission, UserPermission, NereidAnonymousUser
from .website import WebSite, WebSiteLocale, WebsiteCountry, \
    WebsiteCurrency, WebsiteWebsiteLocale
from .urls import URLMap, URLRule, URLRuleDefaults
from .static_file import NereidStaticFolder, NereidStaticFile
from .currency import Currency
from .template import ContextProcessors
from .configuration import NereidConfigStart, NereidConfig
from .translation import Translation, TranslationSet, TranslationUpdate, \
    TranslationClean
from .country import Country, Subdivision
from .model import ModelData


def register():
    Pool.register(
        Address,
        Party,
        ContactMechanism,
        NereidUser,
        NereidAnonymousUser,
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
        Country,
        Subdivision,
        ModelData,
        module='nereid', type_='model'
    )
    Pool.register(
        NereidConfig,
        TranslationSet,
        TranslationUpdate,
        TranslationClean,
        module='nereid', type_='wizard'
    )
