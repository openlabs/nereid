# This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import re
import os
import sys
import time
import unittest
import ConfigParser
from setuptools import setup, Command


class SQLiteTest(Command):
    """
    Run the tests on SQLite
    """
    description = "Run tests on SQLite"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.environ['TRYTOND_DATABASE_URI'] = 'sqlite://'
        os.environ['DB_NAME'] = ':memory:'

        from tests import suite
        test_result = unittest.TextTestRunner(verbosity=3).run(suite())

        if test_result.wasSuccessful():
            sys.exit(0)
        sys.exit(-1)


class PostgresTest(Command):
    """
    Run the tests on Postgres.
    """
    description = "Run tests on Postgresql"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.environ['TRYTOND_DATABASE_URI'] = 'postgresql://'
        os.environ['DB_NAME'] = 'test_' + str(int(time.time()))

        from tests import suite
        test_result = unittest.TextTestRunner(verbosity=3).run(suite())

        if test_result.wasSuccessful():
            sys.exit(0)
        sys.exit(-1)


class RunAudit(Command):
    """Audits source code using PyFlakes for following issues:
        - Names which are used but not defined or used before they are defined.
        - Names which are redefined without having been used.
    """
    description = "Audit source code with PyFlakes"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys
        try:
            import pyflakes.scripts.pyflakes as flakes
        except ImportError:
            print "Audit requires PyFlakes installed in your system."
            sys.exit(-1)

        warns = 0
        # Define top-level directories
        dirs = ('.')
        for dir in dirs:
            for root, _, files in os.walk(dir):
                if root.startswith(('./build')):
                    continue
                for file in files:
                    if file != '__init__.py' and file.endswith('.py'):
                        warns += flakes.checkPath(os.path.join(root, file))
        if warns > 0:
            print "Audit finished with total %d warnings." % warns
        else:
            print "No problems found in sourcecode."


config = ConfigParser.ConfigParser()
config.readfp(open('trytond_nereid/tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()
major_version, minor_version, _ = info.get('version', '0.0.1').split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

install_requires = [
    'pytz',
    'flask>=0.10',
    'flask-wtf',
    'babel',
    'blinker',
    'speaklater',
    'Flask-Babel>=0.9',
    'Flask-Login',
]

MODULE2PREFIX = {
    'email_queue': 'openlabs',
}

for dep in info.get('depends', []):
    if not re.match(r'(ir|res|webdav)(\W|$)', dep):
        install_requires.append(
            '%s_%s >= %s.%s, < %s.%s' % (
                MODULE2PREFIX.get(dep, 'trytond'), dep, major_version,
                minor_version, major_version, minor_version + 1
            )
        )
install_requires.append(
    'trytond >= %s.%s, < %s.%s' %
    (major_version, minor_version, major_version, minor_version + 1)
)

# Testing dependencies
tests_require = [
    'mock',
    'pycountry',
]

setup(
    name='trytond_nereid',
    version=info.get('version'),
    url='http://nereid.openlabs.co.in/docs/',
    license='GPLv3',
    author='Openlabs Technologies & Consulting (P) Limited',
    author_email='info@openlabs.co.in',
    description='Tryton - Web Framework',
    long_description=open('README.rst').read(),
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
    install_requires=install_requires,
    packages=[
        'nereid',
        'nereid.contrib',
        'nereid.tests',
        'trytond.modules.nereid',
        'trytond.modules.nereid.tests',
        'trytond.modules.nereid_test',
    ],
    package_dir={
        'nereid': 'nereid',
        'nereid.contrib': 'nereid/contrib',
        'nereid.tests': 'nereid/tests',
        'trytond.modules.nereid': 'trytond_nereid',
        'trytond.modules.nereid.tests': 'trytond_nereid/tests',
        'trytond.modules.nereid_test': 'nereid_test_module',
    },
    package_data={
        'trytond.modules.nereid': info.get('xml', [])
            + ['tryton.cfg', 'view/*.xml', 'locale/*.po', 'tests/*.rst']
            + ['i18n/*.pot', 'i18n/pt_BR/LC_MESSAGES/*']
            + ['templates/*.*', 'templates/tests/*.*'],
        'trytond.modules.nereid_test': ['*.xml']
            + ['tryton.cfg', 'locale/*.po', 'tests/*.rst']
            + ['templates/*.*', 'templates/tests/*.*'],
    },
    zip_safe=False,
    platforms='any',
    entry_points="""
    [trytond.modules]
    nereid = trytond.modules.nereid
    nereid_test = trytond.modules.nereid_test
    """,
    test_suite='tests.suite',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    cmdclass={
        'audit': RunAudit,
        'test': SQLiteTest,
        'test_on_postgres': PostgresTest,
    },
)
