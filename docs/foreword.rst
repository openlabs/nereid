Foreword
========

Read this before you get started with Nereid. This hopefully answers some
questions about the purpose and goals of the project, and how to make the
most of it.

What is Nereid ?
----------------

Nereid is a web framework built over Flask, with Tryton as a Backend.

What are the uses of Nereid ?
-----------------------------

Nereid can be used to build web applications, that could use Tryton's 
ORM as a backend. While there are no inherent limitations which prevent 
you from using nereid to build any kind of web application, the design 
decision that we made while building nereid itself is tailored to build 
applications which extend the functionality of the ERP system, like 
e-commerce systems, EDI systems, Customer/Supplier Portals etc.

Why Tryton as a backend ?
-------------------------

Well, why not, would be our question to you ? It's scalable, it's flexible 
and offers the best approach we have seen so far into a declarative coding 
pattern for model design in any ORM. The unique way Tryton handles 
inheritance also makes it an excellent choice. In addition to the above, 
Tryton by default has several modules which make designing business 
applications faster in comparison to other frameworks.

Let's say that you want to build a customer portal, (which is our example 
application), all that you need to do from your end is create a module 
which exposes the information that you want to, and leave other stuff like 
order management, account management etc to the existing Tryton modules.

Configuration and Conventions
-----------------------------

Flask has many configuration values, with sensible defaults, and a few
conventions when getting started.  Nereid follows the same pattern of
configuration values where it makes sense to use them. For configurations
which may need to be changed by company or are based on a specific website, the
configuration is done from Tryton on the company or in website settings.
 
Each website that you plan to have, needs to have a subdirectory within the
application's python source tree. By convention a `static` subdirectory with
the static content like CSS and JS is also created within it. While this 
can be changed you usually don't have to, especially when getting started.

Continue to :ref:`installation`, the :ref:`quickstart`, or the
:ref:`advanced_foreword`.
