.. _installation:

Installation
============

Nereid depends on a handful of Python libraries including Tryton.

So how do you get all that on your system quickly?  There are many ways you
could do that, but the most kick-ass method is `virtualenv`_. The `Flask
Documentation`_ has a detailed `section on using virtualenv`_ to install
Flask. You could refer to the same and then follow the instructions below.

.. _virtualenv:

virtualenv
----------

`virtualenvs`_ are isolated Python environments.

If you are on Mac OS X or Linux, chances are that one of the following two
commands will work for you in creating a virtualenv:

.. code-block:: sh

    $ sudo easy_install virtualenv

or even better

.. code-block:: sh

    $ sudo pip install virtualenv

One of these will probably install virtualenv on your system.  Maybe it's even
in your package manager.  If you use Ubuntu, try

.. code-block:: sh

    $ sudo apt-get install python-virtualenv

If you are on Windows and don't have the `easy_install` command, you must
install it first.  Check :ref:`windows-easy-install` section for more
information about how to do that.  Once you have it installed, run the same
commands as above, but without the `sudo` prefix.

Once you have virtualenv installed, just fire up a shell and create
your own environment.  I usually create a project folder and a `venv`
folder within


.. code-block:: sh

    $ mkdir myproject
    $ cd myproject
    $ virtualenv venv
    New python executable in venv/bin/python
    Installing distribute............done.

Now, whenever you want to work on a project, you only have to activate the
corresponding environment.  On OS X and Linux, do the following:

.. code-block:: sh

    $ . venv/bin/activate

If you are a Windows user, the following command is for you:

.. code-block:: sh

    $ venv\scripts\activate

Either way, you should now be using your virtualenv (notice how the prompt of
your shell has changed to show the active environment).

Now you can just enter the following command to get Nereid activated in your
virtualenv:


.. code-block:: sh

    $ pip install Nereid 

A few seconds, and you are good to go.


System-Wide Installation
------------------------

This is possible as well, though I do not recommend it.  Just run
`pip` with root privileges

.. code-block:: sh

    $ sudo pip install Nereid 

(On Windows systems, run it in a command-prompt window with administrator
privileges, and leave out `sudo`.)


Living on the Edge
------------------

If you want to work with the latest version of Nereid, you can tell
it to operate on a git checkout.  Either way, virtualenv is recommended.

Get the git checkout in a new virtualenv and run in development mode

.. code-block:: sh

    $ git clone http://github.com/openlabs/nereid.git
    Initialized empty Git repository in ~/dev/nereid/.git/
    $ cd nereid 
    $ virtualenv venv --distribute
    New python executable in venv/bin/python
    Installing distribute............done.
    $ . venv/bin/activate
    $ python setup.py develop
    ...
    Finished processing dependencies for Nereid 

This will pull in the dependencies and activate the git head as the current
version inside the virtualenv.  Then all you have to do is run ``git pull
origin`` to update to the latest version.


.. _windows-easy-install:

`pip` and `distribute` on Windows
-----------------------------------

On Windows, installation of `easy_install` is a bit tricky, but still
achievable.  Read the section on `pip and distribute on Windows`_ on the
Flask documentation for a better understanding.


.. _cloning_for_dev:

Cloning for Development
-----------------------

If you are cloning the repository for development or updating the
documentation, you also need to initialise the git submodules for the
theme used in the documentation.

.. code-block:: sh
    :emphasize-lines: 4,6 

    $ git clone http://github.com/openlabs/nereid.git
    Initialized empty Git repository in ~/dev/nereid/.git/
    $ cd nereid
    $ git submodule init
    Submodule 'docs/_themes' (git://github.com/openlabs/flask-sphinx-themes.git) registered for path 'docs/_themes'
    $ git submodule update
    Submodule path 'docs/_themes': checked out 'revision #'


.. _pip and distribute on Windows: http://flask.pocoo.org/docs/installation/#pip-and-distribute-on-windows
.. _virtualenvs: http://www.virtualenv.org/en/latest/index.html
.. _section on using virtualenv: http://flask.pocoo.org/docs/installation/#virtualenv
.. _Flask Documentation: http://flask.pocoo.org/docs/
