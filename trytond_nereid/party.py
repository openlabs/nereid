# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import random
import string
import urllib

try:
    import hashlib
except ImportError:
    hashlib = None
    import sha

import pytz
from wtforms import Form, TextField, IntegerField, SelectField, validators, \
    PasswordField
from wtfrecaptcha.fields import RecaptchaField
from werkzeug import redirect, abort

from nereid import request, url_for, render_template, login_required, flash, \
    jsonify
from nereid.globals import session, current_app
from nereid.signals import registration
from nereid.templating import render_email
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool, Not
from trytond.transaction import Transaction
from trytond.config import CONFIG
from trytond.tools import get_smtp_server
from trytond import backend
from sql import As, Literal, Column

from .i18n import _, get_translations

__all__ = ['Address', 'Party', 'NereidUser',
           'ContactMechanism', 'Permission', 'UserPermission']


class RegistrationForm(Form):
    "Simple Registration form"

    def _get_translations(self):
        """
        Provide alternate translations factory.
        """
        return get_translations()

    name = TextField(_('Name'), [validators.Required(), ])
    email = TextField(_('e-mail'), [validators.Required(), validators.Email()])
    password = PasswordField(_('New Password'), [
        validators.Required(),
        validators.EqualTo('confirm', message=_('Passwords must match'))])
    confirm = PasswordField(_('Confirm Password'))

    if 're_captcha_public' in CONFIG.options:
        captcha = RecaptchaField(
            public_key=CONFIG.options['re_captcha_public'],
            private_key=CONFIG.options['re_captcha_private'],
            secure=True
        )


class AddressForm(Form):
    """
    A form resembling the party.address
    """
    def _get_translations(self):
        """
        Provide alternate translations factory.
        """
        return get_translations()

    name = TextField(_('Name'), [validators.Required(), ])
    street = TextField(_('Street'), [validators.Required(), ])
    streetbis = TextField(_('Street (Bis)'))
    zip = TextField(_('Post Code'), [validators.Required(), ])
    city = TextField(_('City'), [validators.Required(), ])
    country = SelectField(_('Country'), [validators.Required(), ], coerce=int)
    subdivision = IntegerField(_('State/County'), [validators.Required()])
    email = TextField(_('Email'))
    phone = TextField(_('Phone'))


class NewPasswordForm(Form):
    """
    Form to set a new password
    """
    def _get_translations(self):
        """
        Provide alternate translations factory.
        """
        return get_translations()

    password = PasswordField(_('New Password'), [
        validators.Required(),
        validators.EqualTo('confirm', message=_('Passwords must match'))])
    confirm = PasswordField(_('Repeat Password'))


class ChangePasswordForm(NewPasswordForm):
    """
    Form to change the password
    """
    def _get_translations(self):
        """
        Provide alternate translations factory.
        """
        return get_translations()

    old_password = PasswordField(_('Old Password'), [validators.Required()])


STATES = {
    'readonly': Not(Bool(Eval('active'))),
}


class Address:
    """Party Address"""
    __name__ = 'party.address'
    __metaclass__ = PoolMeta

    registration_form = RegistrationForm

    phone = fields.Function(fields.Char('Phone'), 'get_address_mechanism')
    email = fields.Function(fields.Char('E-Mail'), 'get_address_mechanism')

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        Party = pool.get('party.party')
        ContactMechanism = pool.get('party.contact_mechanism')
        TableHandler = backend.get('TableHandler')
        cursor = Transaction().cursor
        table = TableHandler(cursor, cls, module_name)
        party = Party.__table__()
        address = cls.__table__()
        mechanism = ContactMechanism.__table__()

        super(Address, cls).__register__(module_name)

        # Migration from 2.8: move phone and email to contact mechanisms
        for column in ['email', 'phone']:
            if table.column_exist(column):
                join = address.join(
                    party, condition=(party.id == address.party)
                )
                select = join.select(
                    address.create_date, address.create_uid,
                    address.write_date, address.write_uid,
                    As(Literal(column), 'type'),
                    As(Column(address, column), 'value'), address.party,
                    As(Literal(True), 'active'),
                    where=(Column(address, column) != '')
                )
                insert = mechanism.insert(
                    columns=[
                            mechanism.create_date,
                            mechanism.create_uid, mechanism.write_date,
                            mechanism.write_uid, mechanism.type,
                            mechanism.value, mechanism.party, mechanism.active,
                    ], values=select)
                cursor.execute(*insert)

                table.column_rename(column, '%s_deprecated' % column)

    def get_address_mechanism(self, name):
        for mechanism in self.party.contact_mechanisms:
            if mechanism.type == name:
                return mechanism.value
        return ''

    @classmethod
    @login_required
    def edit_address(cls, address=None):
        """
        Create/Edit an Address

        POST will create a new address or update and existing address depending
        on the value of address.
        GET will return a new address/existing address edit form

        :param address: ID of the address
        """
        pool = Pool()
        ContactMechanism = pool.get('party.contact_mechanism')
        form = AddressForm(request.form, name=request.nereid_user.display_name)
        countries = [
            (c.id, c.name) for c in request.nereid_website.countries
        ]
        form.country.choices = countries
        if address not in (a.id for a in request.nereid_user.party.addresses):
            address = None
        if request.method == 'POST' and form.validate():
            mechanisms = []
            party = request.nereid_user.party
            if address is not None:
                cls.write([cls(address)], {
                    'name': form.name.data,
                    'street': form.street.data,
                    'streetbis': form.streetbis.data,
                    'zip': form.zip.data,
                    'city': form.city.data,
                    'country': form.country.data,
                    'subdivision': form.subdivision.data,
                })
            else:
                cls.create([{
                    'name': form.name.data,
                    'street': form.street.data,
                    'streetbis': form.streetbis.data,
                    'zip': form.zip.data,
                    'city': form.city.data,
                    'country': form.country.data,
                    'subdivision': form.subdivision.data,
                    'party': party.id,
                }])
            if form.email.data:
                if not ContactMechanism.search(
                        [
                            ('party', '=', party.id),
                            ('type', '=', 'email'),
                            ('value', '=', form.email.data),
                        ]):
                    mechanisms.append({
                        'party': request.nereid_user.party.id,
                        'type': 'email',
                        'value': form.email.data,
                    })
            if form.phone.data:
                if not ContactMechanism.search(
                        [
                            ('party', '=', party.id),
                            ('type', '=', 'phone'),
                            ('value', '=', form.phone.data),
                        ]):
                    mechanisms.append({
                        'party': request.nereid_user.party.id,
                        'type': 'phone',
                        'value': form.phone.data,
                    })

            if len(mechanisms) > 0:
                ContactMechanism.create(mechanisms)
            return redirect(url_for('party.address.view_address'))
        elif request.method == 'GET' and address:
            # Its an edit of existing address, prefill data
            address = cls(address)
            form = AddressForm(
                name=address.name,
                street=address.street,
                streetbis=address.streetbis,
                zip=address.zip,
                city=address.city,
                country=address.country and address.country.id,
                subdivision=address.subdivision and address.subdivision.id,
                email=address.email,
                phone=address.phone
            )
            form.country.choices = countries
        return render_template('address-edit.jinja', form=form, address=address)

    @classmethod
    @login_required
    def view_address(cls):
        "View the addresses of user"
        return render_template('address.jinja')


class Party(ModelSQL, ModelView):
    "Party"
    __name__ = 'party.party'

    nereid_users = fields.One2Many('nereid.user', 'party', 'Nereid Users')


class ProfileForm(Form):
    """User Profile Form"""
    display_name = TextField(
        'Display Name', [validators.Required(), ],
        description="Your display name"
    )
    timezone = SelectField(
        'Timezone',
        choices=[(tz, tz) for tz in pytz.common_timezones],
        coerce=unicode, description="Your timezone"
    )
    email = TextField(
        'Email', [validators.Required(), validators.Email()],
        description="Your Login Email. This Cannot be edited."
    )


class NereidUser(ModelSQL, ModelView):
    """
    Nereid Users
    """
    __name__ = "nereid.user"
    _rec_name = 'display_name'

    party = fields.Many2One(
        'party.party', 'Party', required=True,
        ondelete='CASCADE', select=1
    )

    display_name = fields.Char('Display Name', required=True)

    #: The email of the user is also the login name/username of the user
    email = fields.Char("e-Mail", select=1)

    #: The password is the user password + the salt, which is
    #: then hashed together
    password = fields.Sha('Password')

    #: The salt which was used to make the hash is separately
    #: stored. Needed for
    salt = fields.Char('Salt', size=8)

    #: A unique activation code required to match the user's request
    #: for activation of the account.
    activation_code = fields.Char('Unique Activation Code')

    # The company of the website(s) to which the user is affiliated. This
    # allows websites of the same company to share authentication/users. It
    # does not make business or technical sense to have website of multiple
    # companies share the authentication.
    #
    # .. versionchanged:: 0.3
    #     Company is mandatory
    company = fields.Many2One('company.company', 'Company', required=True)

    timezone = fields.Selection(
        [(x, x) for x in pytz.common_timezones], 'Timezone', translate=False
    )

    permissions = fields.Many2Many(
        'nereid.permission-nereid.user',
        'nereid_user', 'permission', 'Permissions'
    )

    def get_permissions(self):
        """
        Returns all the permissions as a list of names
        """
        # TODO: Cache this value for each user to avoid hitting the database
        # everytime.
        return frozenset([p.value for p in self.permissions])

    def has_permissions(self, perm_all=None, perm_any=None):
        """Check if the user has all required permissions in perm_all and
        has any permission from perm_any for access

        :param perm_all: A set/frozenset of all permission values/keywords.
        :param perm_any: A set/frozenset of any permission values/keywords.

        :return: True/False
        """
        if not perm_all and not perm_any:
            # Access allowed if no permission is required
            return True
        if not isinstance(perm_all, (set, frozenset)):
            perm_all = frozenset(perm_all if perm_all else [])
        if not isinstance(perm_any, (set, frozenset)):
            perm_any = frozenset(perm_any if perm_any else [])
        current_user_permissions = self.get_permissions()

        if perm_all and not perm_all.issubset(current_user_permissions):
            return False
        if perm_any and not perm_any.intersection(current_user_permissions):
            return False
        return True

    @staticmethod
    def default_timezone():
        return "UTC"

    @staticmethod
    def default_company():
        return Transaction().context.get('company') or False

    @classmethod
    def __setup__(cls):
        super(NereidUser, cls).__setup__()
        cls._sql_constraints += [
            ('unique_email_company', 'UNIQUE(email, company)',
                'Email must be unique in a company'),
        ]

    def _activate(self, activation_code):
        """
        Activate the User account

        .. note::
            This method will raise an assertion error if the activation_code is
            not valid.

        :param activation_code: The activation code used
        :return: True if the activation code was correct
        """
        assert self.activation_code == activation_code, \
            'Invalid Activation Code'
        return self.write([self], {'activation_code': None})

    @staticmethod
    def get_registration_form():
        """
        Returns a registration form for use in the site

        .. tip::

            Configuration of re_captcha

            Remember to forward X-Real-IP in the case of Proxy servers

        """
        # Add re_captcha if the configuration has such an option
        if 're_captcha_public' in CONFIG.options:
            registration_form = RegistrationForm(
                request.form, captcha={'ip_address': request.remote_addr}
            )
        else:
            registration_form = RegistrationForm(request.form)

        return registration_form

    @classmethod
    def registration(cls):
        """
        Invokes registration of an user
        """
        Party = Pool().get('party.party')

        registration_form = cls.get_registration_form()

        if request.method == 'POST' and registration_form.validate():
            existing = cls.search([
                ('email', '=', request.form['email']),
                ('company', '=', request.nereid_website.company.id),
            ]
            )
            if existing:
                flash(_(
                    'A registration already exists with this email. '
                    'Please contact customer care')
                )
            else:
                party = Party(name=registration_form.name.data)
                party.addresses = []
                party.save()
                nereid_user = cls(**{
                    'party': party.id,
                    'display_name': registration_form.name.data,
                    'email': registration_form.email.data,
                    'password': registration_form.password.data,
                    'company': request.nereid_website.company.id,
                }
                )
                nereid_user.save()
                nereid_user.create_act_code()
                registration.send(nereid_user)
                nereid_user.send_activation_email()
                flash(
                    _('Registration Complete. Check your email for activation')
                )
                return redirect(
                    request.args.get('next', url_for('nereid.website.home'))
                )

        return render_template('registration.jinja', form=registration_form)

    def send_activation_email(self):
        """
        Send an activation email to the user

        :param nereid_user: The browse record of the user
        """
        email_message = render_email(
            CONFIG['smtp_from'], self.email, _('Account Activation'),
            text_template='emails/activation-text.jinja',
            html_template='emails/activation-html.jinja',
            nereid_user=self
        )
        server = get_smtp_server()
        server.sendmail(
            CONFIG['smtp_from'], [self.email], email_message.as_string()
        )
        server.quit()

    @classmethod
    @login_required
    def change_password(cls):
        """
        Changes the password

        .. tip::
            On changing the password, the user is logged out and the login page
            is thrown at the user
        """
        form = ChangePasswordForm(request.form)

        if request.method == 'POST' and form.validate():
            if request.nereid_user.match_password(form.old_password.data):
                cls.write(
                    [request.nereid_user],
                    {'password': form.password.data}
                )
                flash(
                    _('Your password has been successfully changed! '
                        'Please login again')
                )
                session.pop('user')
                return redirect(url_for('nereid.website.login'))
            else:
                flash(_("The current password you entered is invalid"))

        return render_template(
            'change-password.jinja', change_password_form=form
        )

    @classmethod
    @login_required
    def new_password(cls):
        """Create a new password

        .. tip::

            Unlike change password this does not demand the old password.
            And hence this method will check in the session for a parameter
            called allow_new_password which has to be True. This acts as a
            security against attempts to POST to this method and changing
            password.

            The allow_new_password flag is popped on successful saving

        This is intended to be used when a user requests for a password reset.
        """
        form = NewPasswordForm(request.form)

        if request.method == 'POST' and form.validate():
            if not session.get('allow_new_password', False):
                current_app.logger.debug('New password not allowed in session')
                abort(403)

            cls.write(
                [request.nereid_user],
                {'password': form.password.data}
            )
            session.pop('allow_new_password')
            flash(_(
                'Your password has been successfully changed! '
                'Please login again'))
            session.pop('user')
            return redirect(url_for('nereid.website.login'))

        return render_template('new-password.jinja', password_form=form)

    def activate(self, activation_code):
        """A web request handler for activation

        :param activation_code: A 12 character activation code indicates reset
            while 16 character activation code indicates a new registration
        """
        try:
            self._activate(activation_code)
        except AssertionError:
            flash(_('Invalid Activation Code'))
        else:
            # Log the user in since the activation code is correct
            session['user'] = self.id

            # Redirect the user to the correct location according to the type
            # of activation code.
            if len(activation_code) == 12:
                session['allow_new_password'] = True
                return redirect(url_for('nereid.user.new_password'))
            elif len(activation_code) == 16:
                flash(_('Your account has been activated'))
                return redirect(url_for('nereid.website.home'))

        return redirect(url_for('nereid.website.login'))

    def create_act_code(self, code_type="new"):
        """Create activation code

        A 12 character activation code indicates reset while 16
        character activation code indicates a new registration

        :param user_id: ID of the User
        :param code_type:   "new" for new activation code
                            "reset" for resetting existing account
        """
        assert code_type in ("new", "reset")
        length = 16 if code_type == "new" else 12

        act_code = ''.join(
            random.sample(string.letters + string.digits, length)
        )
        return self.write([self], {'activation_code': act_code})

    @classmethod
    def reset_account(cls):
        """
        Reset the password for the user.

        .. tip::
            This does NOT reset the password, but just creates an activation
            code and sends the link to the email of the user. If the user uses
            the link, he can change his password.
        """
        if request.method == 'POST':
            user_ids = cls.search(
                [
                    ('email', '=', request.form['email']),
                    ('company', '=', request.nereid_website.company.id),
                ]
            )

            if not user_ids or not request.form['email']:
                flash(_('Invalid email address'))
                return render_template('reset-password.jinja')

            nereid_user, = user_ids

            nereid_user.create_act_code("reset")
            nereid_user.send_reset_email()
            flash(_('An email has been sent to your account for resetting'
                    ' your credentials'))
            return redirect(url_for('nereid.website.login'))

        return render_template('reset-password.jinja')

    def send_reset_email(self):
        """
        Send an account reset email to the user

        :param nereid_user: The browse record of the user
        """
        email_message = render_email(
            CONFIG['smtp_from'], self.email, _('Account Password Reset'),
            text_template='emails/reset-text.jinja',
            html_template='emails/reset-html.jinja',
            nereid_user=self
        )
        server = get_smtp_server()
        server.sendmail(
            CONFIG['smtp_from'], [self.email], email_message.as_string()
        )
        server.quit()

    def match_password(self, password):
        """
        Checks if 'password' is the same as the current users password.

        :param password: The password of the user (string or unicode)
        :return: True or False
        """
        password += self.salt or ''
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        if hashlib:
            digest = hashlib.sha1(password).hexdigest()
        else:
            digest = sha.new(password).hexdigest()
        return (digest == self.password)

    @classmethod
    def authenticate(cls, email, password):
        """Assert credentials and if correct return the
        browse record of the user

        :param email: email of the user
        :param password: password of the user
        :return:
            Browse Record: Successful Login
            None: User cannot be found or wrong password
            False: Account is inactive
        """

        users = cls.search([
            ('email', '=', request.form['email']),
            ('company', '=', request.nereid_website.company.id),
        ])

        if not users:
            current_app.logger.debug("No user with email %s" % email)
            return None

        if len(users) > 1:
            current_app.logger.debug('%s has too many accounts' % email)
            return None

        user, = users
        if user.activation_code and len(user.activation_code) == 16:
            # A new account with activation pending
            current_app.logger.debug('%s not activated' % email)
            flash(_("Your account has not been activated yet!"))
            return False  # False so to avoid `invalid credentials` flash

        if user.match_password(password):
            # Reset any reset activation code that might be there since its a
            # successful login with the old password
            if user.activation_code:
                cls.write([user], {'activation_code': None})
            return user

        return None

    @staticmethod
    def _convert_values(values):
        """
        A helper method which looks if the password is specified in the values.
        If it is, then the salt is also made and added

        :param values: A dictionary of field: value pairs
        """
        if 'password' in values and values['password']:
            values['salt'] = ''.join(random.sample(
                string.ascii_letters + string.digits, 8))
            values['password'] += values['salt']

        return values

    @classmethod
    def create(cls, vlist):
        """
        Create, but add salt before saving

        :param vlist: List of dictionary of Values
        """
        vlist = [cls._convert_values(vals.copy()) for vals in vlist]
        return super(NereidUser, cls).create(vlist)

    @classmethod
    def write(cls, nereid_users, values):
        """
        Update salt before saving
        """
        return super(NereidUser, cls).write(
            nereid_users, cls._convert_values(values)
        )

    @staticmethod
    def get_gravatar_url(email, **kwargs):
        """
        Return a gravatar url for the given email

        :param email: e-mail of the user
        :param https: To get a secure URL
        :param default: The default image to return if there is no profile pic
                        For example a unisex avatar
        :param size: The size for the image
        """
        if kwargs.get('https', request.scheme == 'https'):
            url = 'https://secure.gravatar.com/avatar/%s?'
        else:
            url = 'http://www.gravatar.com/avatar/%s?'
        url = url % hashlib.md5(email.lower()).hexdigest()

        params = []
        default = kwargs.get('default', None)
        if default:
            params.append(('d', default))

        size = kwargs.get('size', None)
        if size:
            params.append(('s', str(size)))

        return url + urllib.urlencode(params)

    def get_profile_picture(self, **kwargs):
        """
        Return the url to the profile picture of the user.

        The default implementation fetches the profile image of the user from
        gravatar using :meth:`get_gravatar_url`
        """
        return self.get_gravatar_url(self.email, **kwargs)

    @staticmethod
    def aslocaltime(naive_date, local_tz_name=None):
        """
        Returns a localized time using `pytz.astimezone` method.

        :param naive_date: a naive datetime (datetime with no timezone
                           information), which is assumed to be the UTC time.
        :param local_tz_name: The timezone in which the date has to be returned
        :type local_tz_name: string

        :return: A datetime object with local time
        """

        utc_date = pytz.utc.localize(naive_date)

        if not local_tz_name:
            return utc_date

        local_tz = pytz.timezone(local_tz_name)
        if local_tz == pytz.utc:
            return utc_date

        return utc_date.astimezone(local_tz)

    def as_user_local_time(self, naive_date):
        """
        Returns a date localized in the user's timezone.

        :param naive_date: a naive datetime (datetime with no timezone
                           information), which is assumed to be the UTC time.
        """
        return self.aslocaltime(naive_date, self.timezone)

    @classmethod
    @login_required
    def profile(cls):
        """
        User profile
        """
        user_form = ProfileForm(request.form, obj=request.nereid_user)
        if request.method == 'POST' and user_form.validate():
            cls.write(
                [request.nereid_user], {
                    'display_name': user_form.display_name.data,
                    'timezone': user_form.timezone.data,
                }
            )
            flash('Your profile has been updated.')
            return redirect(
                request.args.get('next', url_for('nereid.user.profile'))
            )
        return render_template(
            'profile.jinja', user_form=user_form, active_type_name="general"
        )


class ContactMechanismForm(Form):
    type = SelectField('Type', [validators.Required()])
    value = TextField('Value', [validators.Required()])
    comment = TextField('Comment')


class ContactMechanism(ModelSQL, ModelView):
    """
    Allow modification of contact mechanisms
    """
    __name__ = "party.contact_mechanism"

    @classmethod
    def get_form(cls):
        """
        Returns the contact mechanism form
        """
        from trytond.modules.party import contact_mechanism
        form = ContactMechanismForm(request.form)
        form.type.choices = contact_mechanism._TYPES
        return form

    @login_required
    def add(self):
        """
        Adds a contact mechanism to the party's contact mechanisms
        """
        form = self.get_form()
        if form.validate():
            self.create({
                'party': request.nereid_user.party.id,
                'type': form.type.data,
                'value': form.value.data,
                'comment': form.comment.data,
            })
            if request.is_xhr:
                return jsonify({'success': True})
            return redirect(request.referrer)

        if request.is_xhr:
            return jsonify({'success': False})
        else:
            for field, messages in form.errors:
                flash("<br>".join(messages), "Field %s" % field)
            return redirect(request.referrer)

    @login_required
    def remove(self):
        """
        :param record_id: Delete the contat mechanism with the given ID
        """
        record_id = request.form.get('record_id', type=int)
        if not record_id:
            abort(404)

        record = self.browse(record_id)
        if not record:
            abort(404)
        if record.party == request.nereid_user.party:
            self.delete(record_id)
        else:
            abort(403)
        if request.is_xhr:
            return jsonify({
                'success': True
            })
        return redirect(request.referrer)


class Permission(ModelSQL, ModelView):
    "Nereid Permissions"
    __name__ = 'nereid.permission'

    name = fields.Char('Name', required=True, select=True)
    value = fields.Char('Value', required=True, select=True)
    nereid_users = fields.Many2Many(
        'nereid.permission-nereid.user',
        'permission', 'nereid_user', 'Nereid Users'
    )

    @classmethod
    def __setup__(cls):
        super(Permission, cls).__setup__()
        cls._sql_constraints += [
            ('unique_value', 'UNIQUE(value)',
                'Permissions must be unique by value'),
        ]


class UserPermission(ModelSQL):
    "Nereid User Permissions"
    __name__ = 'nereid.permission-nereid.user'

    permission = fields.Many2One(
        'nereid.permission', 'Permission',
        ondelete='CASCADE', select=True, required=True
    )
    nereid_user = fields.Many2One(
        'nereid.user', 'User',
        ondelete='CASCADE', select=True, required=True
    )
