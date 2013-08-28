'''
    Nereid

    Nereid - Tryton as a web framework

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
from setuptools import setup

setup(
    name='Nereid',
    version='2.6.0.8',
    url='http://nereid.openlabs.co.in/docs/',
    license='GPLv3',
    author='Openlabs Technologies & Consulting (P) Limited',
    author_email='info@openlabs.co.in',
    description='Tryton - Web Framework',
    long_description=__doc__,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Tryton',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=[
        'distribute',
        'trytond_nereid>=2.6,<2.7',
        'flask<0.10',
        'wtforms',
        'wtforms-recaptcha',
        'babel',
        'speaklater',
        'Flask-Babel>=0.9',
    ],
    packages=[
        'nereid',
        'nereid.contrib',
        'nereid.tests',
    ],
    package_dir={
        'nereid': 'nereid',
        'nereid.contrib': 'nereid/contrib',
        'nereid.tests': 'tests',
    },
    zip_safe=False,
    platforms='any',
)
