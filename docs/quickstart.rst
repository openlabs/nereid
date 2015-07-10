.. _quickstart:

Quickstart
==========

Eager to get started? This page gives a good introduction to Nereid.  It
assumes you already have Nereid installed.  If you do not, head over to the
:ref:`installation` section.

A minimal application
======================

A minimal Nereid application first requries a Tryton database with the
Nereid module installed. If you already have a database with Nereid
installed, head over to `creating website`_.

Setting up a database
`````````````````````

TODO

.. _creating website:

Creating a new website
``````````````````````

Once the nereid module is installed in a Tryton database, open the
`Websites` menu under `Nereid/Configuration`, and create a new
website with the following settings. 

    +-----------+-------------------------------+
    | **Field** | **Value**                     |
    +-----------+-------------------------------+
    | Name      | abcpartnerportal.com          |
    +-----------+-------------------------------+
    | URL Map   | Choose `Default`              |
    +-----------+-------------------------------+
    | Company   | Choose any                    |
    +-----------+-------------------------------+
    | Default   | English                       |
    | Language  |                               |
    +-----------+-------------------------------+
    | Guest User| Create a new Nereid User      |
    +-----------+-------------------------------+
    | App User  | Create or choose a User       |
    +-----------+-------------------------------+
    

Refer to the :py:class:`trytond_nereid.routing.WebSite` for details on 
what each of the fields mean.




.. tip::
    Since version 2.0.0.3 the name of the website is used by the WSGI
    dispatcher to identify the website that needs to be served. When you
    test the site locally, it is not usually possible to mimic your
    production url. This can be overcome by using a simple WSGI middleware
    which overwrite HTTP_HOST in the environ.

.. _creating_application:

Creating the application and template
`````````````````````````````````````

Once the website is created, a python script which loads nereid and runs
the application needs to be written. This script is used to load Nereid,
configure your application settings and also serves as an APP_MODULE if
you plan to use WSGI HTTP servers like `Gunicorn`_ 

.. code-block:: python

    #!/usr/bin/env python
    from nereid import Nereid

    CONFIG = dict(

        # The name of database
        DATABASE_NAME = 'nereid',

        # Static file root. The root location of the static files. The static/ will
        # point to this location. It is recommended to use the web server to serve
        # static content
        STATIC_FILEROOT = 'static/',

        # Tryton Config file path
        TRYTON_CONFIG = '../etc/trytond.conf',

        # If the application is to be configured in the debug mode
        DEBUG = False,

        # Load the template from FileSystem in the path below instead of the 
        # default Tryton loader where templates are loaded from Database
        TEMPLATE_LOADER_CLASS = 'nereid.templating.FileSystemLoader',
        TEMPLATE_SEARCH_PATH = '.',
    )

    # Create a new application
    app = Nereid()

    # Update the configuration with the above config values
    app.config.update(CONFIG)

    # Initialise the app, connect to cache and backend
    app.initialise()


    class NereidHostChangeMiddleware(object):
        """
        A middleware which alters the HTTP_HOST so that you can test
        the site locally. This middleware replaces the HTTP_HOST with
        the value you prove to the :attr: site

        :param app: The application for which the middleware needs to work
        :param site: The value which should replace HTTP_HOST WSGI Environ
        """
        def __init__(self, app, site):
            self.app = app
            self.site = site

        def __call__(self, environ, start_response):
            environ['HTTP_HOST'] = self.site
            return self.app(environ, start_response)


    if __name__ == '__main__':
        # The name of the website
        site = 'abcpartnerportal.com'

        app.wsgi_app = NereidHostChangeMiddleware(app.wsgi_app, site)
        app.debug = True
        app.static_folder = '%s/static' % site
        app.run('0.0.0.0')


You can now test run the application

.. code-block:: sh

    $ python application.py

The above command launches a single threaded HTTP Server for debugging
purposes which listens to the port 5000. Point your browser to
`localhost:5000 <http://localhost:5000/>`_ and you should now be able to
see a debug screen, with the `~jinja2.exceptions.TemplateNotFound`
Exception and its traceback. This is because you have not defined the
template yet.

.. _define_template:

Defining the templates
``````````````````````

For this quickstart section we will load the templates from the filesystem
as we have used the :py:class:`~nereid.templating.FileSystemLoader` as 
Template Loader in the application config. The template loader looks up 
templates in the folder for the site that is currently being rendered. In 
this case the template would be `abcpartnerportal.com/home.jinja`.

Create a template file `home.jinja` in the folder `abcpartnerportal.com`
and fill in the following code

.. code-block:: html

    <html>
    <body>
      <h1>Welcome to Nereid</h1>
    </body>
    </html>

Run the application again and you should be able to see the rendered HTML
on your browser at `localhost:5000 <http://localhost:5000/>`_


.. _Gunicorn: http://gunicorn.org/
