'''
    Nereid

    Nereid - Tryton as a web framework

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details
'''
import re

from setuptools import setup


trytond_module_info = eval(open('trytond_nereid/__tryton__.py').read())
major_version, minor_version, _ = trytond_module_info.get(
    'version', '0.0.1').split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

tryton_requires = []
for dep in trytond_module_info.get('depends', []):
    if not re.match(r'(ir|res|workflow|webdav)(\W|$)', dep):
        tryton_requires.append('trytond_%s >= %s.%s, < %s.%s' %
                (dep, major_version, minor_version, major_version,
                    minor_version + 1))


setup(
    name='Nereid',
    version='0.3',
    url='http://openlabs.co.in/nereid',
    license='GPLv3',
    author='Openlabs Technologies & Consulting (P) Limited',
    author_email='info@openlabs.co.in',
    description='Tryton - Web Framework',
    long_description=__doc__,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    install_requires=[
        'distribute',
        'trytond>=2.0,<2.1',
        'flask>=0.8,<0.9',
        'wtforms',
        'wtforms-recaptcha',
        'ccy',
        'babel',
        'speaklater',
        'Flask-Babel',
    ] + tryton_requires,
    packages=[
        'nereid',
        'nereid.contrib',
        'nereid.contrib.testing',
        'nereid_tests',

        'trytond.modules.nereid',
        'trytond.modules.nereid.tests',
    ],
    package_dir={
        'nereid': 'nereid',
        'nereid.contrib': 'nereid/contrib',
        'nereid.contrib.testing': 'nereid/contrib/testing',
        'nereid_tests': 'tests',

        'trytond.modules.nereid': 'trytond_nereid',
        'trytond.modules.nereid.tests': 'trytond_nereid/tests',

    },
    package_data = {
        'trytond.modules.nereid': trytond_module_info.get('xml', []) \
                + trytond_module_info.get('translation', []) \
                + ['i18n/*.pot', 'i18n/pt_BR/LC_MESSAGES/*'],
    },
    zip_safe=False,
    platforms='any',
    entry_points="""
    [trytond.modules]
    nereid = trytond.modules.nereid
    """,

    tests_require=[
        'unittest2',
        'minimock',
    ],
    test_suite = "nereid_tests.test_runner.suite"
)
