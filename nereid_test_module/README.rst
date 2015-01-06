Nereid Test Module
==================

This module is an optional tryton module which helps in testing nereid
features. This module is not required for the regular functioning of
nereid but if you are developing on nereid, you could use this module to
write tests.

History
-------

Version 3.4.0.1
```````````````

The module ws brought back into nereid codebase because the changes on
both module happen at the same time and tracking the changes in different
places is not worth the effort.

TODO: Try and disable the module from being displayed in the modules list
of Tryton for regular implementations.

Version 2.8.0.2
```````````````

This module was originally a part of nereid itself and then moved out as
nereid is to be a part of tryton. This module can be added to the
test_requires list of your module if you use it in testing.
