==================================
Nereid Testing Scenarios
==================================

=============
General Setup
=============

Imports::

    >>> from decimal import Decimal
    >>> import datetime
    >>> import socket
    >>> from dateutil.relativedelta import relativedelta
    >>> from proteus import config, Model, Wizard
    >>> from nereid import Nereid, render_template
    >>> from trytond.config import CONFIG

Create database::

    >>> DBNAME = ':memory:'
    >>> config = config.set_trytond(DBNAME, database_type='sqlite')

Install Nereid::

    >>> Module = Model.get('ir.module.module')
    >>> modules = Module.find([('name', '=', 'nereid')])
    >>> len(modules)
    1

    >>> Module.button_install([x.id for x in modules], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('start')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> Company = Model.get('company.company')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> company.name = 'OTCL'
    >>> company.currency, = Currency.find([('code', '=', 'EUR')])
    >>> company_config.execute('add')
    >>> company, = Company.find()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create parties::

    >>> Party = Model.get('party.party')
    >>> Address = Model.get('party.address')
    >>> ContactMechanism = Model.get('party.contact_mechanism')
    >>> customer = Party(name='Customer')
    >>> customer.save() 
    >>> email = ContactMechanism(type='email', value='user@example.com', 
    ...     party=customer)
    >>> email.save()
    >>> Address.write(customer.addresses[0].id, dict(
    ...     name='Customer Address', email=email.id, password='password'), {})
    True
    >>> customer.reload()

Setup URLs::

    >>> NereidSite = Model.get('nereid.website')
    >>> URLMap = Model.get('nereid.url_map')
    >>> URLRule = Model.get('nereid.url_rule')
    >>> url_map, = URLMap.find([])

Create Templates::

    >>> LangObj = Model.get('ir.lang')
    >>> english, = LangObj.find([('code', '=', 'en_US')])
    >>> Template = Model.get('nereid.template')
    >>> address_template = Template(
    ...     name='address.jinja', language=english,
    ...     source='address')
    >>> address_template.save()
    >>> address_edit_template = Template(
    ...     name='address-edit.jinja', language=english,
    ...     source='address-edit:{{ form.errors }}')
    >>> address_edit_template.save()

Setup Site::

    >>> Country = Model.get('country.country')
    >>> countries = [c.id for c in Country.find([('code', 'in', ('IN', 'AU'))])]
    >>> site = NereidSite(name='Test Site', 
    ...     url_map=url_map, company=company.id, countries=countries,)
    >>> site.save()

Load the WSGI App::

    >>> from nereid import Nereid
    >>> app = Nereid(
    ...     DATABASE_NAME=DBNAME,
    ...     TRYTON_CONFIG='trytond.conf',
    ...     SITE=site.name,)
    >>> app.debug=True
    >>> app.site
    u'Test Site'

Try getting address::

    >>> with app.test_client() as client:
    ...     client.post('/login', 
    ...         data=dict(email='user@example.com', password='password'))
    ...     client.get('/view-address')
    <Response streamed [302 FOUND]>
    <Response streamed [200 OK]>
    >>> len(customer.addresses)
    1

Create a new address::

    >>> country, = Country.find([('id', '=', countries[0])])
    >>> data = {
    ...     'name': 'New Address', 'street': 'xyz', 'zip': 'M145EU',
    ...     'country': country.id, 'subdivision': country.subdivisions[0].id,
    ...     'city': 'Coimbatore'
    ...     }   
    >>> with app.test_client() as client:
    ...     client.post('/login', 
    ...         data=dict(email='user@example.com', password='password'))
    ...     client.post('/save-new-address', data=data)
    <Response streamed [302 FOUND]>
    <Response streamed [302 FOUND]>
    >>> customer.reload()
    >>> len(customer.addresses)
    2
    >>> address_2 = customer.addresses[-1]
    >>> address_2.name == data['name']
    True
    >>> address_2.street == data['street']
    True

Configure Email account::

    >>> CONFIG['smtp_server'] = 'smtp.dummysmtp.com'
    >>> CONFIG['smtp_user'] = 'sharoonthomas'
    >>> CONFIG['smtp_password'] = '981dcdfb8f794b3fa84bd294b7bfaa08'

Try resetting the account::

    >>> address = customer.addresses[0]
    >>> address.activation_code
    >>> with app.test_client() as client:
    ...     client.post('/reset-account', 
    ...         data=dict(email='user@example.com'))
    <Response streamed [302 FOUND]>
    >>> address.reload()
    >>> address.activation_code != False
    True
    >>> old_password = address.password
    >>> with app.test_client() as client:
    ...     client.get(
    ...         '/activate-account/%s/%s' % (address.id, 
    ...             address.activation_code))
    ...     client.post('/change-password', 
    ...         data={'password': 'new', 'confirm': 'new'})
    <Response streamed [302 FOUND]>
    <Response streamed [302 FOUND]>
    >>> address.reload()
    >>> old_password != address.password
    True

Setup a  second website::

    >>> site2 = NereidSite(name='Test Site 2', 
    ...     url_map=url_map, company=company.id, countries=countries,)

    >>> site2.save()
    >>> app2 = Nereid(
    ...     DATABASE_NAME=DBNAME,
    ...     TRYTON_CONFIG='trytond.conf',
    ...     SITE=site2.name,)
    >>> app2.debug=True
    >>> app2.site
    u'Test Site 2'

Try with same name template and lang in current website::

    >>> t1 = Template(
    ...     name='unique.jinja', language=english,
    ...     website=site.id, source='site1')
    >>> t1.save()
    >>> t2 = Template(
    ...     name='unique.jinja', language=english,
    ...     website=site2.id, source='site2')
    >>> t2.save()
    >>> with app.test_request_context('/'):
    ...     with app.transaction:
    ...         render_template('unique.jinja')
    u'site1'
    >>> with app2.test_request_context('/'):
    ...     with app2.transaction:
    ...         render_template('unique.jinja')
    u'site2'
