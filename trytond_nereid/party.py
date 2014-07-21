# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import warnings
from flask_wtf import Form
from wtforms import TextField, IntegerField, SelectField, validators
from werkzeug import redirect, abort
from jinja2 import TemplateNotFound

from nereid import request, url_for, render_template, login_required, flash, \
    jsonify, route, current_user
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond import backend
from sql import As, Literal, Column
from .user import RegistrationForm
from .i18n import _

__all__ = ['Address', 'Party', 'ContactMechanism']


class AddressForm(Form):
    """
    A form resembling the party.address
    """
    name = TextField(_('Name'), [validators.Required(), ])
    street = TextField(_('Street'), [validators.Required(), ])
    streetbis = TextField(_('Street (Bis)'))
    zip = TextField(_('Post Code'), [validators.Required(), ])
    city = TextField(_('City'), [validators.Required(), ])
    country = SelectField(_('Country'), [validators.Required(), ], coerce=int)
    subdivision = IntegerField(_('State/County'), [validators.Required()])
    email = TextField(_('Email'))
    phone = TextField(_('Phone'))

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        super(AddressForm, self).__init__(formdata, obj, prefix, **kwargs)

        # Fill country choices while form is initialized
        self.country.choices = [
            (c.id, c.name) for c in request.nereid_website.countries
        ]


class Address:
    """Party Address"""
    __name__ = 'party.address'
    __metaclass__ = PoolMeta

    registration_form = RegistrationForm

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

    @classmethod
    def get_address_form(cls, address=None):
        """
        Return an initialised Address form that can be validated and used to
        create/update addresses

        :param address: If an active record is provided it is used to autofill
                        the form.
        """
        if address:
            form = AddressForm(
                request.form,
                name=address.name,
                street=address.street,
                streetbis=address.streetbis,
                zip=address.zip,
                city=address.city,
                country=address.country and address.country.id,
                subdivision=address.subdivision and address.subdivision.id,
                email=address.party.email,
                phone=address.party.phone
            )
        else:
            address_name = "" if request.nereid_user.is_anonymous() else \
                request.nereid_user.display_name
            form = AddressForm(request.form, name=address_name)

        return form

    @classmethod
    @route("/create-address", methods=["GET", "POST"])
    @login_required
    def create_address(cls):
        """
        Create an address for the current nereid_user

        GET
        ~~~

        Return an address creation form

        POST
        ~~~~

        Creates an address and redirects to the address view. If a next_url
        is provided, redirects there.

        .. version_added: 3.0.3.0
        """
        form = cls.get_address_form()

        if request.method == 'POST' and form.validate():
            party = request.nereid_user.party
            address, = cls.create([{
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
                party.add_contact_mechanism_if_not_exists(
                    'email', form.email.data
                )
            if form.phone.data:
                party.add_contact_mechanism_if_not_exists(
                    'phone', form.phone.data
                )
            return redirect(url_for('party.address.view_address'))

        try:
            return render_template('address-add.jinja', form=form)
        except TemplateNotFound:
            # The address-add template was introduced in 3.0.3.0
            # so just raise a deprecation warning till 3.2.X and then
            # expect the use of address-add template
            warnings.warn(
                "address-add.jinja template not found. "
                "Will be required in future versions",
                DeprecationWarning
            )
            return render_template('address-edit.jinja', form=form)

    @classmethod
    @route("/save-new-address", methods=["GET", "POST"])
    @route("/edit-address/<int:address>", methods=["GET", "POST"])
    @login_required
    def edit_address(cls, address=None):
        """
        Edit an Address

        POST will update an existing address.
        GET will return a existing address edit form.

        .. version_changed:: 3.0.3.0

            For creating new address use the create_address handled instead of
            this one. The functionality would be deprecated in 3.2.X

        :param address: ID of the address
        """
        if address is None:
            warnings.warn(
                "Address creation will be deprecated from edit_address handler."
                " Use party.address.create_address instead",
                DeprecationWarning
            )
            return cls.create_address()

        form = cls.get_address_form()

        if address not in (a.id for a in request.nereid_user.party.addresses):
            # Check if the address is in the list of addresses of the
            # current user's party
            abort(403)

        address = cls(address)

        if request.method == 'POST' and form.validate():
            party = request.nereid_user.party
            cls.write([address], {
                'name': form.name.data,
                'street': form.street.data,
                'streetbis': form.streetbis.data,
                'zip': form.zip.data,
                'city': form.city.data,
                'country': form.country.data,
                'subdivision': form.subdivision.data,
            })
            if form.email.data:
                party.add_contact_mechanism_if_not_exists(
                    'email', form.email.data
                )
            if form.phone.data:
                party.add_contact_mechanism_if_not_exists(
                    'phone', form.phone.data
                )
            return redirect(url_for('party.address.view_address'))

        elif request.method == 'GET' and address:
            # Its an edit of existing address, prefill data
            form = cls.get_address_form(address)

        return render_template('address-edit.jinja', form=form, address=address)

    @classmethod
    @route("/view-address", methods=["GET"])
    @login_required
    def view_address(cls):
        "View the addresses of user"
        return render_template('address.jinja')

    @route("/remove-address/<int:active_id>", methods=["POST"])
    @login_required
    def remove_address(self):
        """
        Make address inactive if user removes the address from address book.
        """
        if self.party == current_user.party:
            self.active = False
            self.save()
            flash(_('Address has been deleted successfully!'))
            if request.is_xhr:
                return jsonify(success=True)
            return redirect(request.referrer)

        abort(403)


class Party(ModelSQL, ModelView):
    "Party"
    __name__ = 'party.party'

    nereid_users = fields.One2Many('nereid.user', 'party', 'Nereid Users')

    def add_contact_mechanism_if_not_exists(self, type, value):
        """
        Adds a contact mechanism to the party if it does not exist

        :return: The created contact mechanism or the one which existed
        """
        ContactMechanism = Pool().get('party.contact_mechanism')

        mechanisms = ContactMechanism.search([
            ('party', '=', self.id),
            ('type', '=', type),
            ('value', '=', value),
        ])
        if not mechanisms:
            mechanisms = ContactMechanism.create([{
                'party': self.id,
                'type': type,
                'value': value,
            }])
        return mechanisms[0]


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
        form = ContactMechanismForm()
        form.type.choices = contact_mechanism._TYPES
        return form

    @classmethod
    @route("/contact-mechanisms/add", methods=["POST"])
    @login_required
    def add(cls):
        """
        Adds a contact mechanism to the party's contact mechanisms
        """
        form = cls.get_form()
        if form.validate_on_submit():
            cls.create([{
                'party': request.nereid_user.party.id,
                'type': form.type.data,
                'value': form.value.data,
                'comment': form.comment.data,
            }])
            if request.is_xhr:
                return jsonify({'success': True})
            return redirect(request.referrer)

        if request.is_xhr:
            return jsonify({'success': False})
        else:
            for field, messages in form.errors:
                flash("<br>".join(messages), "Field %s" % field)
            return redirect(request.referrer)

    @route("/contact-mechanisms/<int:active_id>", methods=["POST", "DELETE"])
    @login_required
    def remove(self):
        """
        DELETE: Removes the current contact mechanism
        """
        ContactMechanism = Pool().get('party.contact_mechanism')

        if self.party == request.nereid_user.party:
            ContactMechanism.delete([self])
        else:
            abort(403)
        if request.is_xhr:
            return jsonify({
                'success': True
            })
        return redirect(request.referrer)
