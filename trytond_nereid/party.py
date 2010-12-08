# This file is part of Nereid.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
'''
    nereid_trytond.party

    Partner Address is also considered as the login user

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''
import random
import string

from trytond.model import ModelView, ModelSQL, fields


class Address(ModelSQL, ModelView):
    """An address is considered as the equivalent of a user
    in a conventional Web application. Hence, the username and
    password are stored against the party.address object.
    """
    _name = 'party.address'

    #: The email to which all application related emails like
    #: registration, password reet etc is managed
    email = fields.Many2One('party.contact_mechanism', 'E-Mail')

    #: Similar to email
    phone = fields.Many2One('party.contact_mechanism', 'Phone')

    #: Username for login
    username = fields.Char('Username')

    #: The password is the user password + the salt, which is
    #: then hashed together
    password = fields.Sha('Password')

    #: The salt which was used to make the hash is separately
    #: stored. Needed for 
    salt = fields.Char('Salt')

    def _convert_values(self, values):
        if 'password' in values:
            values['salt'] = ''.join(random.sample(
                string.ascii_letters + string.digits, 8))
            values['password'] += values['salt']
        return values

    def create(self, values):
        """
        Create, but add salt before saving

        :param values: Dictionary of Values
        """
        return super(Address, self).create(
            self._convert_values(values)
            )

    def write(self, ids, values):
        """
        Update salt before saving

        :param ids: IDs of the records
        :param values: Dictionary of values
        """
        return super(Address, self).write(
            ids, self._convert_values(values)
            )
Address()
