#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from werkzeug import redirect, abort
from werkzeug.utils import cached_property
from flask.wrappers import Request as RequestBase, Response as ResponseBase
from .helpers import url_for
from .globals import current_app, session


def _get_website_name(host):
    """
    The host could have the host_name and port number. This will try
    to get the best possible guess of the website name from the host name
    """
    #XXX: Needs improvement
    return host.split(':')[0]


class Request(RequestBase):
    "Request Object"

    @cached_property
    def nereid_website(self):
        """Fetch the Browse Record of current website."""
        Website = current_app.pool.get('nereid.website')
        return Website.search([
            ('name', '=', _get_website_name(self.host))]
        )[0]

    @cached_property
    def nereid_user(self):
        """Fetch the browse record of current user or None."""
        NereidUser = current_app.pool.get('nereid.user')
        if 'user' not in session:
            return NereidUser(self.nereid_website.guest_user.id)

        try:
            nereid_user, = NereidUser.search([('id', '=', session['user'])])
        except ValueError:
            session.pop('user')
            abort(redirect(url_for('nereid.website.login')))
        else:
            return nereid_user

    @cached_property
    def nereid_currency(self):
        """
        Return a browse record for the currency.
        """
        return self.nereid_locale.currency

    @cached_property
    def nereid_locale(self):
        """
        Returns the active record of the current locale.
        The locale could either be from the URL if the locale was specified
        in the URL, or the default locale from the website.
        """
        if self.view_args and 'locale' in self.view_args:
            for locale in self.nereid_website.locales:
                if locale.code == self.view_args['locale']:
                    return locale

        # Return the default locale
        return self.nereid_website.default_locale

    @cached_property
    def nereid_language(self):
        """
        Return a active record for the language.
        """
        return self.nereid_locale.language

    @cached_property
    def is_guest_user(self):
        """Return true if the user is guest."""
        return ('user' not in session)


class Response(ResponseBase):
    pass
