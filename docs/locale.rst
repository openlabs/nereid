.. _locale:

Internationalized Websites
==========================

The locale model which is part of nereid allows you to build web
applications capable of being used across users of different languages and
currencies. This guide explains the design behind locales.


Single Locale
-------------

If your application caters to users of a signle region you may not want
your application to be available in multiple locales. In this case you can
leave the `Available Locales` field in the website settings empty.

Multiple Locales
----------------

If your application caters to multiple locales, the first step would be
creating the required locales. Locales once created can be reused across
multiple websites.

Creating a locale
`````````````````

Every locale consists of a `code` which is also used as a prefix in the
URL path.

* **code**: The `code` is used as a prefix in the URL when the application
  has multiple locales. An example of such a code could be `en-us`.
* **language**: The tryton `language` that should be used when the locale
  is chosen. Considering the above example of code (`en-us`), the language
  could be `en_US` (available at installation with Tryton).
* **currency**: The tryton `currency` that should be used when the locale
  is chosen. Considering the above example the currency could be `USD`.

This design allows your application to adapt to most requirements of
localisation. For example if your web application has to be available to
users in Spain, France and Belgium and has content in English, French and 
Spanish, a good way to use locales would be:

============== ======================== ======================
 Code           Langauge                 Currency               
============== ======================== ======================
 en             en_GB                    EUR                    
 fr             fr_FR                    EUR                    
 es             es_ES                    EUR                    
============== ======================== ======================

URLs
````

Once the locales are added to available locales of a website, the
application begins to prefix the code to the URLs. For example, the home
page which was previously available on `http://example.com/` would now be
available on `http://example.com/en-us` assuming en-us is the code of a
locale in your setup.


.. tip::

   The application needs to be restarted if it is already running for the
   URL changes to take effect.

Pro-Tip: Migrating from Single Locale to Multiple Locales
---------------------------------------------------------

You may have started off with a single locale website and you now want to
start using multiple locales. Search engines may have already indexed your
site and users may already have bookmarks and you do not want to break
your website. The best way to handle such a situation would be to create
redirects in your `web server configuration <https://www.digitalocean.com/community/articles/how-to-create-temporary-and-permanent-redirects-with-apache-and-nginx>`_.


Similarly if you want to fallback to single locale from multiple locales,
web server redirects are your best tools for the job.
