# QT GUI elements

This is the solution of the various items 



## Display of best practices

### Helper QWidget container

Custom Qt containers to help with common patterns will always be declared with
the `_Q` prefix, and be declared in the `qt_helper.py` file.

### Clarifying the layout related codes

For display elements that will typically interact with the logical sections
should be declared with a typical field name. For pure layout-related display
elements, these elements should be prefixed with an underscore `_` when
decalring the field, and be constructed in a separate `__init_layout__` method.

