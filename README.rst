Nereid for Tryton
=================

.. image:: https://secure.travis-ci.org/openlabs/nereid.png?branch=develop
  :target: https://travis-ci.org/openlabs/nereid

.. image:: https://coveralls.io/repos/openlabs/nereid/badge.png
  :target: https://coveralls.io/r/openlabs/nereid

Nereid is a web framework built over Flask, with Tryton as an ORM.

Copyright
---------

Read COPYRIGHT

License
-------

GPL3 - Read LICENSE

Installation
------------

From PyPI using pip::

    pip install trytond_nereid

Using github repository::

    git clone git@github.com:openlabs/nereid.git
    cd nereid
    python setup.py install

Translation
-----------

Best practice for Nereid Translations is a little bit different from the
usual procedure due to the different nature of the translatable messages
in Nereid. For best results the following workflow is recommended:

- Import translations as usual by installing the module with the desired
  language.

- Run 'Set translations' to import new messages into the database.

- This is the additional step recommended in Nereid:
  Run 'Update translations' just once to get the new translations copied
  to your language *and* updated with the proposal evtl. found on an (old)
  existent string.

- Run 'Clean translations' to remove obsolete messages, that could lead
  to errors in translation mechanism and that are needless to translate.

- Now work on 'Update translations' the second time on a clean set of
  the actual messages. Don't forget to control and unmark fuzzy messages
  that got a proposal from an old string.

- When done, run as usual 'Export translations'.

- Enjoy!

.. note:: When working on translations to be included in the upstream
        package, please work on a clean template tree without
        customizations.


FAQ
---

What are the uses of Nereid ?
`````````````````````````````

Nereid can be used to build web applications, that could use Tryton's 
ORM as a backend. While, there are no inherent limitations which prevent
you from using nereid to build any kind of web application, the design
decision that we made while building nereid itself are tailored to build
application that extend the functionality of the ERP system, like 
e-commerce system, EDI systems, Customer/Supplier Portals etc.

Why Tryton as a backend ?
`````````````````````````

Well, why not would be our question to you ? It's scalable, it's flexible
and offers the best approach we have seen so far into a declarative coding
pattern for model design in any ORM. The unique way Tryton handles inheritance
also makes it an excellent choice. In addition to the above, Tryton by default
has several modules which make designing business applications faster in 
comparison to other frameworks.

Let's say that you want to build a customer portal, (which is our example 
application), all that you need to do from your end is create a module which
exposes the information that you want to, and leave other stuff like order
management, account management etc to the existing Tryton modules.

Which version of Tryton does nereid use ?
`````````````````````````````````````````

Nereid is available for version 2.0, 2.4, 2.6, 2.8, 3.0 and 3.2.

All versions other than 3.2 and 3.0 are mainteinance only releases.

Now that brings us to how versioning is done

Nereid being a module for tryton, follows the same release process of Tryton
with a few differences. The repository is maintained on Github and each
version of Nereid is separately maintained on a git branch.

Specific minor releases can be identified from git tags or downloaded from
the tags page on github. All minor releases are available on PYPI too.

What is the license of Nereid ?
```````````````````````````````

Nereid follows the same license as that of Tryton which is GPLv3. Have a 
problem with that ? Contact us and we will be glad to help you out!

How do I install nereid ?
`````````````````````````

Just clone the module and run the python setup file. It installs all 
the dependencies too.

::

    $ git clone git://github.com/openlabs/nereid.git
    $ cd nereid
    $ python setup.py install

Is nereid modular ?
```````````````````

Depends on what you think modular is. For us we think Nereid is modular 
because you could separate logically different functionality into a 
separate Tryton module and then the functionality would be available 
to you depending on what modules are installed in the database that you
are accessing.

This also allows modules to be reused. For example, the nereid-catalog
module which makes product information available could just be used for
a display only catalog and is also used as the cart display module for
nereid-webshop - the full eCommerce system.

A little history
````````````````

The initial goal was to build an e-commerce system over OpenERP/Odoo 
called Callisto, and we did! It worked, but never scaled on OpenERP.
The license sucked (surprise)! and then we saw that most issues we saw
with OpenERP don't exist in Tryton. And, we were right.

If you want to know more about why we made these design decisions, 
feel free to drop us a mail

Authors and Contributors
````````````````````````

Nereid was built at `Openlabs <http://www.openlabs.co.in>`_. It's now 
opensource, feel free to fork and contribute! Hate us! Just fork You 
can get hold of @openlabsindia or @sharoonthomas if you have some 
techy questions to drill with.

Support or Contact
``````````````````

Having trouble with Nereid? Check out the documentation at TODO or 
contact sales@openlabs.co.in and we’ll help you sort it out.
