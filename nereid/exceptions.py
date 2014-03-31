# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from werkzeug.exceptions import NotFound


class WebsiteNotFound(NotFound):
    description = 'The requested website was not found on the server.'
