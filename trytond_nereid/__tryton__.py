# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

{
    'name': 'Nereid',
    'version': '2.4.0.7dev',
    'author': 'Openlabs Technologies & Consulting (P) Limited',
    'email': 'info@openlabs.co.in',
    'website': 'http://www.openlabs.co.in/',
    'description': '''Base configuration of Nereid:

    1. Routing: Sites, URL Maps
    ''',
    'depends': [
        'ir',
        'res',
        'company',
    ],
    'xml': [
       'configuration.xml',
       'static_file.xml',
       'urls.xml',
       'party.xml',
       'lang.xml',
    ],
    'translation': [
    ],
}

