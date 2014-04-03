# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from warnings import warn
warn(DeprecationWarning("Use nereid.sessions instead"))

from .sessions import (Session, NullSession, MemcachedSessionStore,  # noqa
    NereidSessionInterface)
