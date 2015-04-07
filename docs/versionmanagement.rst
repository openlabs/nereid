.. _versionmanagement:

Version Management
==================

The Version number of Nereid and its module have two parts. The first part
indicates the version of Tryton the module is written for and the second
part indicates the revision of the module for that series of Tryton.

Let us consider the version number `2.0.0.3`, `2.0` indicates that the
module works with the Version `2.0` of Tryton and that the module is in
the `0.3` revision for the `2.0` series of Tryton.

When a newer, stable version of Tryton is relased by the maintainers,
nereid will also be updated to be compatible for the new version. When
this is done, the previous version of the module is pushed to `maintenance
branch`_.

When updating to a newer series of Tryton, the minor revision begins again
from `0.1`. For example, if `2.4.0.6` is the last stable version of a
nereid module in the 2.4 series and an update to `2.6` series is made, the
version of the module would be `2.6.0.1`.

Development Versions
--------------------

To differentiate between a stable version and a development version Tryton
uses BSD style even and odd numbers. For example `2.3` indicates a
development release of tryton while `2.4` would be the stable version
resulting from such development. However, it is not feasible to use the
same with Nereid since, we would begin to migrate modules only after a
stable version of Tryton would be released.

Therefore, it is necessary to identify if the revision you see on the
repository is a stable tip or a development one. For the same, we suffix
the version number with `dev`. Note that the development version
`2.4.0.1dev` is a version before `2.4.0.1`::

    >>> from pkg_resources import parse_version
    >>> parse_version('2.4.0.1dev') < parse_version('2.4.0.1')
    True

.. _maintenance branch:

Maintenance Branch
------------------

Maintenance branches of current revisions are created whenever a newer 
version of Tryton is available and the module is updated to the newer 
version. As of now, the latest available stable release of 
Tryton is 2.4 and the upcoming 2.6 release has a major change to include 
the active record design pattern. When the 2.6 version is released the 
current master branch will be checked out to a new branch called 
`2.4-maintenance` and no further active development will be done on it.

At any point of time, the number of previous releases maintained would be
the same as that of Tryton. For example if Tryton release management team
stops maintaining version `2.0`, the same would happen with Nereid.

.. note::

   Critical bug fixes and security updates will be performed on maintenace
   releases.
