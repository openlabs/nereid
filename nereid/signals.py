# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from flask.signals import (template_rendered, request_started,  # noqa
    request_finished, got_request_exception, _signals,
    request_tearing_down)


#: Login signal
#:  - This signal is triggered when a succesful login takes place
login = _signals.signal('login')

#: Failed Login
#:  - This signal is raised when a login fails
failed_login = _signals.signal('failed-login')

#: Logout
#: Triggered when a logout occurs
logout = _signals.signal('logout')

#: Registration
#: Triggered when a user registers
registration = _signals.signal('registration')


transaction_start = _signals.signal('nereid.transaction.start')
transaction_stop = _signals.signal('nereid.transaction.stop')
