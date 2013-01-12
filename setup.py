'''
    Nereid

    Nereid - Tryton as a web framework

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
import re

from setuptools import setup, Command

class RunTests(Command):
    description = "Run tests"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys,subprocess
        errno = subprocess.call([sys.executable, 'trytond_nereid/tests/__init__.py'])
        raise SystemExit(errno)


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
    version=trytond_module_info.get('version'),
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
        'trytond>=2.4,<2.5',
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
        'nereid.tests',

        'trytond.modules.nereid',
        'trytond.modules.nereid.tests',
    ],
    package_dir={
        'nereid': 'nereid',
        'nereid.contrib': 'nereid/contrib',
        'nereid.tests': 'tests',

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
        'mock',
        'pycountry',
    ],
    cmdclass={
        'test': RunTests,
    },
)
