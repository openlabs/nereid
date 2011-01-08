'''
    Nereid

    Nereid - Tryton as a web framework

    :copyright: (c) 2010 by Sharoon Thomas.
    :license: BSD, see LICENSE for more details
'''
from setuptools import Command, setup
import re

try:
    import trytond
    tryton_installed = True
except ImportError:
    tryton_installed = False

requires = ['flask']
package_dir = {'nereid': 'nereid'}
package_data = { }
entry_points = ''
packages = ['nereid',]


if tryton_installed:
    trytond_module_info = eval(open('trytond_nereid/__tryton__.py').read())
    major_version, minor_version, _ = trytond_module_info.get(
        'version', '0.0.1').split('.', 2)
    major_version = int(major_version)
    minor_version = int(minor_version)

    for dep in trytond_module_info.get('depends', []):
        if not re.match(r'(ir|res|workflow|webdav)(\W|$)', dep):
            requires.append('trytond_%s >= %s.%s, < %s.%s' %
                    (dep, major_version, minor_version, major_version,
                        minor_version + 1))
    requires.append('trytond >= %s.%s, < %s.%s' %
            (major_version, minor_version, major_version, minor_version + 1))
    package_dir.update({'trytond.modules.nereid': 'trytond_nereid'})
    package_data.update({
        'trytond.modules.nereid': trytond_module_info.get('xml', []) \
                + trytond_module_info.get('translation', []),
        })
    entry_points += """
    [trytond.modules]
    nereid = trytond.modules.nereid
    """
    packages.append('trytond.modules.nereid')


setup(
    name='Nereid',
    version='0.1',
    url='http://openlabs.co.in/nereid',
    license='GPLv3',
    author='Sharoon Thomas',
    author_email='sharoon.thomas@openlabs.co.in',
    description='Tryton - Web Framework extension',
    long_description=__doc__,
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'flask',
        'wtforms',
    ],
    entry_points=entry_points,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)


