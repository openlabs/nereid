trytond-nereid
==============

This is the Tryton module required for nereid to work.

.. image:: https://travis-ci.org/openlabs/trytond-nereid.png?branch=feature/2.6

Copyright
---------

Read COPYRIGHT

License
-------

GPL3 - Read LICENSE

Installation
------------

Read INSTALL


Using Babel to translate trytond-nereid
---------------------------------------

The basic steps in translation are:

  * Extract translations
  * Create language/locales
  * Translate them
  * compile the translations

To extract translations
```````````````````````

    pybabel extract -F babel.cfg -o i18n/messages.pot .


To Translate to new language
`````````````````````````````

    pybabel init -i i18n/messages.pot -d i18n -l pt_BR


Now edit the translations/de/LC_MESSAGES/messages.po file as needed. 
Check out some gettext tutorials if you feel lost.


To compile the translations for use
```````````````````````````````````


    pybabel compile -d i18n


What if the strings change?
```````````````````````````


    pybabel update -i i18n/messages.pot -d i18n


Afterwards some strings might be marked as fuzzy (where it tried to figure out if a 
translation matched a changed key). If you have fuzzy entries, make sure to check 
them by hand and remove the fuzzy flag before compiling. 
