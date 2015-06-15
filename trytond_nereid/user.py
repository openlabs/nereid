# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import random
import string
import urllib
import base64

try:
    import hashlib
except ImportError:
    hashlib = None
    import sha

import pytz
from flask_wtf import Form, RecaptchaField
from wtforms import TextField, SelectField, validators, PasswordField
from flask.ext.login import logout_user, AnonymousUserMixin, login_url
from werkzeug import redirect, abort

from nereid import request, url_for, render_template, login_required, flash, \
    jsonify, route
from nereid.ctx import has_request_context
from nereid.globals import current_app
from nereid.signals import registration
from nereid.templating import render_email
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.pyson import Eval, Bool, Not
from trytond.transaction import Transaction
from trytond.config import CONFIG
from trytond.tools import get_smtp_server
from trytond import backend
from itsdangerous import URLSafeSerializer, TimestampSigner, SignatureExpired, \
    BadSignature, TimedJSONWebSignatureSerializer
from .i18n import _

__all__ = ['NereidUser', 'NereidAnonymousUser', 'Permission', 'UserPermission']


class RegistrationForm(Form):
    "Simple Registration form"
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


class NewPasswordForm(Form):
    """
    Form to set a new password
    """
    password = PasswordField(_('New Password'), [
        validators.Required(),
        validators.EqualTo('confirm', message=_('Passwords must match'))])
    confirm = PasswordField(_('Repeat Password'))


class ChangePasswordForm(NewPasswordForm):
    """
    Form to change the password
    """
    old_password = PasswordField(_('Old Password'), [validators.Required()])


STATES = {
    'readonly': Not(Bool(Eval('active'))),
}


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


class ResetAccountForm(Form):
    """Reset Account Form"""
    email = TextField(
        'Email', [validators.Required(), validators.Email()],
        description="Your Login Email."
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

    email_verified = fields.Boolean("Email Verified")
    active = fields.Boolean('Active')

    @staticmethod
    def default_email_verified():
        return False

    @staticmethod
    def default_active():
        """
        If the user gets created from the web the activation should happen
        through the activation link. However, users created from tryton
        interface are activated by default
        """
        if has_request_context():
            return False
        return True

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get("TableHandler")
        table = TableHandler(Transaction().cursor, cls, module_name)
        user = cls.__table__()

        super(NereidUser, cls).__register__(module_name)

        # Migrations
        if table.column_exist('activation_code'):
            # Migration for activation_code field
            # Set the email_verification and active based on activation code
            user.update(
                columns=[user.active, user.email_verified],
                values=[True, True],
                where=(user.activation_code == None)
            )
            # Finally drop the column
            table.drop_column('activation_code', exception=True)

    def serialize(self, purpose=None):
        """
        Return a JSON serializable object that represents this record
        """
        return {
            'id': self.id,
            'email': self.email,
            'display_name': self.display_name,
            'permissions': list(self.get_permissions()),
        }

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

    @property
    def _signer(self):
        return TimestampSigner(current_app.secret_key)

    @property
    def _serializer(self):
        return URLSafeSerializer(current_app.secret_key)

    def _get_sign(self, salt):
        """
        Returns a timestampsigned, url_serialized sign  with a salt
        'verification'.
        """
        return self._signer.sign(self._serializer.dumps(self.id, salt=salt))

    def get_email_verification_link(self, **options):
        """
        Returns an email verification link for the user
        """
        return url_for(
            'nereid.user.verify_email',
            sign=self._get_sign('verification'),
            active_id=self.id,
            **options
        )

    def get_activation_link(self, **options):
        """
        Returns an activation link for the user
        """
        return url_for(
            'nereid.user.activate',
            sign=self._get_sign('activation'),
            active_id=self.id,
            **options
        )

    def get_reset_password_link(self, **options):
        """
        Returns a password reset link for the user
        """
        return url_for(
            'nereid.user.new_password',
            sign=self._get_sign('reset-password'),
            active_id=self.id,
            **options
        )

    @classmethod
    def build_response(cls, message, response, xhr_status_code):
        """
        Method to handle response for jinja and XHR requests.

        message: Message to show as flash and send as json response.
        response: redirect or render_template method.
        xhr_status_code: Status code to be sent with json response.
        """
        if request.is_xhr or request.is_json:
            return jsonify(message=message), xhr_status_code
        flash(_(message))
        return response

    @route("/verify-email/<int:active_id>/<sign>", methods=["GET"])
    def verify_email(self, sign, max_age=24 * 60 * 60):
        """
        Verifies the email and redirects to home page. This is a method in
        addition to the activate method which activates the account in addition
        to verifying the email.
        """
        try:
            unsigned = self._serializer.loads(
                self._signer.unsign(sign, max_age=max_age),
                salt='verification'
            )
        except SignatureExpired:
            return self.build_response(
                'The verification link has expired',
                redirect(url_for('nereid.website.home')), 400
            )
        except BadSignature:
            return self.build_response(
                'The verification token is invalid!',
                redirect(url_for('nereid.website.home')), 400
            )
        else:
            if self.id == unsigned:
                self.email_verified = True
                self.save()
                return self.build_response(
                    'Your email has been verified!',
                    redirect(url_for('nereid.website.home')), 200
                )
            else:
                return self.build_response(
                    'The verification token is invalid!',
                    redirect(url_for('nereid.website.home')), 400
                )

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
                captcha={'ip_address': request.remote_addr}
            )
        else:
            registration_form = RegistrationForm()

        return registration_form

    @classmethod
    @route("/registration", methods=["GET", "POST"])
    def registration(cls):
        """
        Invokes registration of an user
        """
        Party = Pool().get('party.party')

        registration_form = cls.get_registration_form()

        if registration_form.validate_on_submit():
            with Transaction().set_context(active_test=False):
                existing = cls.search([
                    ('email', '=', registration_form.email.data),
                    ('company', '=', request.nereid_website.company.id),
                ])
            if existing:
                message = _(
                    'A registration already exists with this email. '
                    'Please contact customer care'
                )
                if request.is_xhr or request.is_json:
                    return jsonify(message=unicode(message)), 400
                else:
                    flash(message)
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
                registration.send(nereid_user)
                nereid_user.send_activation_email()
                message = _(
                    'Registration Complete. Check your email for activation'
                )
                if request.is_xhr or request.is_json:
                    return jsonify(message=unicode(message)), 201
                else:
                    flash(message)
                return redirect(
                    request.args.get('next', url_for('nereid.website.home'))
                )

        if registration_form.errors and (request.is_xhr or request.is_json):
            return jsonify({
                'message': unicode(_('Form has errors')),
                'errors': registration_form.errors,
            }), 400

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
    @route("/change-password", methods=["GET", "POST"])
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
                logout_user()
                return redirect(url_for('nereid.website.login'))
            else:
                flash(_("The current password you entered is invalid"))

        return render_template(
            'change-password.jinja', change_password_form=form
        )

    @route("/new-password/<int:active_id>/<sign>", methods=["GET", "POST"])
    def new_password(self, sign, max_age=24 * 60 * 60):
        """Create a new password

        This is intended to be used when a user requests for a password reset.
        The link sent out to reset the password will be a timestamped sign
        which is validated for max_age before allowing the user to set the
        new password.
        """
        form = NewPasswordForm()
        if form.validate_on_submit():
            try:
                unsigned = self._serializer.loads(
                    self._signer.unsign(sign, max_age=max_age),
                    salt='reset-password'
                )
            except SignatureExpired:
                return self.build_response(
                    'The password reset link has expired',
                    redirect(url_for('nereid.website.login')), 400
                )
            except BadSignature:
                return self.build_response(
                    'Invalid reset password code',
                    redirect(url_for('nereid.website.login')), 400
                )
            else:
                if not self.id == unsigned:
                    current_app.logger.debug('Invalid reset password code')
                    abort(403)

                self.write([self], {'password': form.password.data})
                return self.build_response(
                    'Your password has been successfully changed! '
                    'Please login again',
                    redirect(url_for('nereid.website.login')), 200
                )
        elif form.errors:
            if request.is_xhr or request.is_json:
                return jsonify(error=form.errors), 400
            flash(_('Passwords must match'))

        return render_template(
            'new-password.jinja', password_form=form, sign=sign, user=self
        )

    @route("/activate-account/<int:active_id>/<sign>", methods=["GET"])
    def activate(self, sign, max_age=24 * 60 * 60):
        """A web request handler for activation of the user account. This
        method verifies the email and if it succeeds, activates the account.

        If your workflow requires a manual approval of every account, override
        this to not activate an account, or make a no op out of this method.

        If all what you require is verification of email, `verify_email` method
        could be used.
        """
        try:
            unsigned = self._serializer.loads(
                self._signer.unsign(sign, max_age=max_age),
                salt='activation'
            )
        except SignatureExpired:
            flash(_("The activation link has expired"))
        except BadSignature:
            flash(_("The activation token is invalid!"))
        else:
            if self.id == unsigned:
                self.active = True
                self.email_verified = True
                self.save()
                flash(_('Your account has been activated. Please login now.'))
            else:
                flash(_('Invalid Activation Code'))

        return redirect(url_for('nereid.website.login'))

    @classmethod
    @route("/reset-account", methods=["GET", "POST"])
    def reset_account(cls):
        """
        Reset the password for the user.

        .. tip::
            This does NOT reset the password, but just creates an activation
            code and sends the link to the email of the user. If the user uses
            the link, he can change his password.
        """
        form = ResetAccountForm()
        if form.validate_on_submit():
            try:
                nereid_user, = cls.search([
                    ('email', '=', form.email.data),
                    ('company', '=', request.nereid_website.company.id),
                ])
            except ValueError:
                return cls.build_response(
                    'Invalid email address',
                    render_template('reset-password.jinja'),
                    400
                )
            nereid_user.send_reset_email()
            return cls.build_response(
                'An email has been sent to your account for resetting'
                ' your credentials',
                redirect(url_for('nereid.website.login')), 200
            )
        elif form.errors:
            if request.is_xhr or request.is_json:
                return jsonify(error=form.errors), 400
            flash(_('Invalid email address.'))

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
        browse record of the user.

        .. versionchanged:: 3.0.4.0

            Does not check if the user account is active or not as that
            is not in the scope of 'authentication'.

        :param email: email of the user
        :param password: password of the user
        :return:
            Browse Record: Successful Login
            None: User cannot be found or wrong password
        """
        if not (email and password):
            return None
        with Transaction().set_context(active_test=False):
            users = cls.search([
                ('email', '=', email),
                ('company', '=', request.nereid_website.company.id),
            ])

        if not users:
            current_app.logger.debug("No user with email %s" % email)
            return None

        if len(users) > 1:
            current_app.logger.debug('%s has too many accounts' % email)
            return None

        user, = users
        if user.match_password(password):
            return user

        return None

    @classmethod
    def load_user(cls, user_id):
        """
        Implements the load_user method for Flask-Login

        :param user_id: Unicode ID of the user
        """
        try:
            with Transaction().set_context(active_test=False):
                user, = cls.search([('id', '=', int(user_id))])
        except ValueError:
            return None

        # Instead of returning the active record returned in the above search
        # we are creating a new record here. This is because the returned
        # active record seems to carry around the context setting of
        # active_test and any nested lookup from the record will result in
        # records being fetched which are inactive.
        return cls(int(user_id))

    @classmethod
    def load_user_from_header(cls, header_val):
        """
        Implements the header_loader method for Flask-Login

        :param header_val: Value of the header
        """
        # Basic authentication
        if header_val.startswith('Basic '):
            header_val = header_val.replace('Basic ', '', 1)
            try:
                header_val = base64.b64decode(header_val)
            except TypeError:
                pass
            else:
                user = cls.authenticate(*header_val.split(':', 1))
                if user and user.is_active():
                    return user

        # TODO: Digest authentication

        # Token in Authorization header
        if header_val.startswith(('token ', 'Token ')):
            token = header_val \
                            .replace('token ', '', 1) \
                            .replace('Token ', '', 1)
            return cls.load_user_from_token(token)

    @classmethod
    def load_user_from_token(cls, token):
        """
        Implements the token_loader method for Flask-Login

        :param token: The token sent in the user's request
        """
        serializer = TimedJSONWebSignatureSerializer(
            current_app.secret_key,
            expires_in=current_app.token_validity_duration
        )

        try:
            data = serializer.loads(token)
        except SignatureExpired:
            return None     # valid token, but expired
        except BadSignature:
            return None     # invalid token

        user = cls(data['id'])
        if user.password != data['password']:
            # The password has been changed by the user. So the token
            # should also be invalid.
            return None

        if user.is_active():
            # Login only if the login_user method returns True for the user
            return user

    def get_auth_token(self):
        """
        Return an authentication token for the user. The auth token uniquely
        identifies the user and includes the salted hash of the password, then
        encrypted with a Timed serializer.

        The token_validity_duration can be set in application configuration
        using TOKEN_VALIDITY_DURATION
        """
        serializer = TimedJSONWebSignatureSerializer(
            current_app.secret_key,
            expires_in=current_app.token_validity_duration
        )
        local_txn = None
        if Transaction().cursor is None:
            # Flask-Login can call get_auth_token outside the context
            # of a nereid transaction. If that is the case, launch a
            # new transaction here.
            local_txn = Transaction().start(
                current_app.database_name, 0, readonly=True
            )
            self = self.__class__(self.id)
        try:
            return serializer.dumps({'id': self.id, 'password': self.password})
        finally:
            if local_txn is not None:
                Transaction().stop()

    @classmethod
    def unauthorized_handler(cls):
        """
        This is called when the user is required to log in.

        If the request is XHR, then a JSON message with the status code 401
        is sent as response, else a redirect to the login page is returned.
        """
        if request.is_xhr:
            rv = jsonify(message="Bad credentials")
            rv.status_code = 401
            return rv
        return redirect(
            login_url(current_app.login_manager.login_view, request.url)
        )

    def is_authenticated(self):
        """
        Returns True if the user is authenticated, i.e. they have provided
        valid credentials. (Only authenticated users will fulfill the criteria
        of login_required.)
        """
        return bool(self.id)

    def is_active(self):
        return bool(self.active)

    def is_anonymous(self):
        return not self.id

    def get_id(self):
        return unicode(self.id)

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
    @route("/me", methods=["GET", "POST"])
    @login_required
    def profile(cls):
        """
        User profile
        """
        user_form = ProfileForm(obj=request.nereid_user)
        if user_form.validate_on_submit():
            cls.write(
                [request.nereid_user], {
                    'display_name': user_form.display_name.data,
                    'timezone': user_form.timezone.data,
                }
            )
            flash('Your profile has been updated.')

        if request.is_xhr or request.is_json:
            return jsonify(request.nereid_user.serialize())

        return render_template(
            'profile.jinja', user_form=user_form, active_type_name="general"
        )


class NereidAnonymousUser(AnonymousUserMixin, ModelView):
    """
    Nereid Anonymous User Object
    """
    __name__ = "nereid.user.anonymous"

    def has_permissions(self, perm_all=None, perm_any=None):
        """
        By default return that the user has no permissions.

        Downstream modules can change this behavior.
        """
        return False

    def get_profile_picture(self, **kwargs):
        """
        Returns the default gravatar mystery man silouette
        """
        User = Pool().get('nereid.user')
        kwargs['default'] = 'mm'
        return User.get_gravatar_url("does not matter", **kwargs)


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
