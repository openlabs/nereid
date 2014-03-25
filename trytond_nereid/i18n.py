# -*- coding: utf-8 -*-
'''

    Internationalisation for Nereid

    :copyright: (c) 2010-2014 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details

'''
from nereid.contrib.locale import make_lazy_gettext, make_lazy_ngettext


_, N_ = make_lazy_gettext('nereid'), make_lazy_ngettext('nereid')
