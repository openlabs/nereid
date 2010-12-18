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
try:
    import hashlib
except ImportError:
    hashlib = None
    import sha

from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval


# pylint: disable-msg=E1101
class Address(ModelSQL, ModelView):
    """An address is considered as the equivalent of a user
    in a conventional Web application. Hence, the username and
    password are stored against the party.address object.
    """
    _name = 'party.address'

    #: The email to which all application related emails like
    #: registration, password reet etc is managed
    email = fields.Many2One('party.contact_mechanism', 'E-Mail',
        domain=[('party', '=', Eval('party')), ('type', '=', 'email')], 
        depends=['party'])

    #: Similar to email
    phone = fields.Many2One('party.contact_mechanism', 'Phone',
        domain=[('party', '=', Eval('party')), ('type', '=', 'phone')], 
        depends=['party'])

    #: The password is the user password + the salt, which is
    #: then hashed together
    password = fields.Sha('Password')

    #: The salt which was used to make the hash is separately
    #: stored. Needed for 
    salt = fields.Char('Salt', size=8)

    def __init__(self):
        super(Address, self).__init__()
        self._sql_constraints += [
            ('unique_email', 'UNIQUE(email)',
                'email must be unique.'),
        ]
        self._error_messages.update({
            'no_email': 'The user does not have an email assigned'
            })
        self._rpc.update({
            'create_web_account': True,
            'reset_web_account': True
            })

    def create_web_account(self, ids):
        """Create a new web account for given address
        """
        for address in self.browse(ids):
            if not address.email:
                self.raise_user_error('no_email')
            password = ''.join(
                random.sample(string.letters + string.digits, 16))
            self.write(address.id, {'password': password})
        return True

    def reset_web_account(self, ids):
        """Reset the password for the user"""
        for address in self.browse(ids):
            if not address.email:
                self.raise_user_error('no_email')
            password = ''.join(
                random.sample(string.letters + string.digits, 16))
            self.write(address.id, {'password': password})
        return True

    def authenticate(self, email, password):
        """Assert credentials and if correct return the
        browse record of the user

        :param email: email of the user
        :param password: password of the user
        :return: Browse Record or None
        """
        contact_mech_obj = self.pool.get('party.contact_mechanism')
        contact = contact_mech_obj.search([
                ('value', '=', email),
                ('type', '=', 'email')])
        if not contact:
            return None

        ids = self.search([
            ('email', '=', contact[0])
            ])
        if not ids or len(ids) > 1:
            return None

        address = self.browse(ids[0])
        password += address.salt or ''

        if isinstance(password, unicode):
            password = password.encode('utf-8')

        if hashlib:
            password_sha = hashlib.sha1(password).hexdigest()
        else:
            password_sha = sha.new(password).hexdigest()

        if password_sha == address.password:
            return address

        return None

    def _convert_values(self, values):
        if 'password' in values and values['password']:
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
