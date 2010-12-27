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

from wtforms import Form, TextField, IntegerField, SelectField, validators, \
    PasswordField
from nereid import request, url_for, render_template, login_required, flash
from nereid.globals import session
from werkzeug import redirect
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval


class AddressForm(Form):
    "A Form resembling the party.address"
    name = TextField('Name', [validators.Required(),])
    street = TextField('Street', [validators.Required(),])
    streetbis = TextField('Street (Bis)')
    zip = TextField('Post Code', [validators.Required(),])
    city = TextField('City', [validators.Required(),])
    country = SelectField('Country', [validators.Required(),], coerce=int)
    subdivision = IntegerField('State/Country', [validators.Required()])


class ChangePasswordForm(Form):
    "Form to change the password"
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password')
    

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

    #: A unique activation code required to match the user's request
    #: for activation of the account.
    activation_code = fields.Char('Unique Activation Code')

    def __init__(self):
        super(Address, self).__init__()
        self._sql_constraints += [
            ('unique_email', 'UNIQUE(email)',
                'email must be unique.'),
            ('unique_activation_code', 'UNIQUE(activation_code)',
                'Activation code must be unique.'),
        ]
        self._error_messages.update({
            'no_email': 'The user does not have an email assigned'
            })
        self._rpc.update({
            'create_web_account': True,
            'reset_web_account': True
            })

    def _activate(self, address_id, activation_code):
        "Activate the address account"
        address = self.browse(address_id)
        assert address.activation_code == activation_code, 'Invalid Act Code'
        return self.write(address.id, {'activation_code': False})

    @login_required
    def change_password(self):
        "Changes the password"
        form = ChangePasswordForm(request.form)
        if request.method == 'POST' and form.validate():
            self.write(request.nereid_user.id, 
                {'password': form.password.data})
            flash('Your password has been successfully changed!')
            return redirect(url_for('nereid.website.login'))
        return render_template('change-password.jinja')

    def activate(self, address_id, activation_code):
        "A web request handler for activation"
        try:
            self._activate(address_id, activation_code)
            session['user'] = address_id
            flash('Your account has been activated')
            return redirect(url_for('party.address.change_password'))
        except AssertionError:
            flash('Invalid Activation Code')
        return redirect(url_for('nereid.website.login'))

    def create_act_code(self, address):
        """Create activation code
        
        :param address: ID of the addresss
        """
        act_code = ''.join(
                random.sample(string.letters + string.digits, 16))
        exists = self.search([('activation_code', '=', act_code)])
        if exists:
            return self.create_act_code(address)
        return self.write(address, {'activation_code': act_code})

    def create_web_account(self, ids):
        """Create a new web account for given address
        """
        for address in self.browse(ids):
            if not address.email:
                self.raise_user_error('no_email')
            self.create_act_code(address.id)
        return True

    def reset_account(self):
        """Reset the password for the user
        
        This is a public interface
        """
        contact_mech_obj = self.pool.get('party.contact_mechanism')

        if request.method == 'POST':
            contact = contact_mech_obj.search([
                    ('value', '=', request.form['email']),
                    ('type', '=', 'email')])
            if not contact:
                flash('Invalid email address')
                return render_template('reset-password.jinja')
            address = self.search([('email', '=', contact[0])])
            if not address:
                flash('Email is not associated with any account.')
                return render_template('reset-password.jinja')

            self.create_act_code(address[0])
            flash('An email has been sent to your account for resetting'
                ' your credentials')
            return redirect(url_for('nereid.website.login'))

        return render_template('reset-password.jinja')

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
        return super(Address, self).create(self._convert_values(values))

    def write(self, ids, values):
        """
        Update salt before saving

        :param ids: IDs of the records
        :param values: Dictionary of values
        """
        return super(Address, self).write(ids, self._convert_values(values))

    @login_required
    def edit_address(self, address=None):
        form = AddressForm(request.form)
        form.country.choices = [
            (c.id, c.name) for c in request.nereid_website.countries
            ]
        if address not in [a.id for a in request.nereid_user.party.addresses]:
            address = None
        if request.method == 'POST' and form.validate():
            if address is not None:
                self.write(address, {
                    'name': form.name.data,
                    'street': form.street.data,
                    'streetbis': form.streetbis.data,
                    'zip': form.zip.data,
                    'city': form.city.data,
                    'country': form.country.data,
                    'subdivision': form.subdivision.data,
                    })
            else:
                self.create({
                    'name': form.name.data,
                    'street': form.street.data,
                    'streetbis': form.streetbis.data,
                    'zip': form.zip.data,
                    'city': form.city.data,
                    'country': form.country.data,
                    'subdivision': form.subdivision.data,
                    'party': request.nereid_user.party.id,
                    })
            return redirect(url_for('party.address.view_address'))
        elif address:
            # Its an edit of existing address, prefill data
            record = self.browse(address)
            form = AddressForm(
                name=record.name,
                street=record.street,
                streetbis=record.streetbis,
                zip=record.zip,
                city=record.city,
                country=record.country.id,
                subdivision=record.subdivision.id
            )
            form.country.choices = [
                (c.id, c.name) for c in request.nereid_website.countries
            ]
        return render_template('address-edit.jinja', form=form)

    @login_required
    def view_address(self):
        "View the addresses of user"
        return render_template('address.jinja')

Address()


class EmailTemplate(ModelSQL, ModelView):
    'add `url_for` to the template context'
    _name = 'electronic_mail.template'

    def template_context(self, record):
        context = super(EmailTemplate, self).template_context(record)
        context['url_for'] = url_for
        return context

EmailTemplate()

