# sfQT GUI elements

This is the session control program displayed as a GUI using PyQt5,
specifically using the QWidgets method of constructing GUI layouts. The overall
structure of this code is that the ["Session"](../session.py) object is handled
by the minimally overloaded GUISession object, which also acts as the main
container QWidget instances for all the vairous display elements.

Individual widgets of a specific function will typically be contained within a
single [_QContainer](qt_helper.py) Widget, which is simply a container that
contains a reference to the main `session` instance (so that arbitrary
functions used to modify the session can be used), we well as additional
structured methods to ensure that the interface can be refreshed from inner
methods.

- For container holding the methods for interacting with hardware interactions.
  See the various containers in the [`hwpanels`](./hwpanels/) directory.
- For container holding the methods for interacting with the session
  loading/unloading, as well as running procedures, see the various containers
  in the [session_browser](./session_browser/) directory.
- The general layout of the session object, see the function defined in
  [`__init__.py`](./__init__.py) file.


## Discussion of some of the best practices

### Helper QWidget container

Custom Qt containers to help with common patterns will always be declared with
the `_Q` prefix, and be declared in the [`qt_helper.py`](./qt_helper.py) file.
Some commonly used method containers would be:

- `_QContainer`: custom container that holds a reference to the parent
  `session` object. This ensures that the contents can be used to interact with
  the session programmatically.
- `_QRunButton`: Buttons that should be used to initiate session interaction
  fucntions. The activation of one of these buttons will immediately lock the
  other `_QRunButton` instances to ensure there are no race-conditions that can
  be initated by the user side. Notice that (unless you know exactly why),
  should should not explicitly disable or enable this type of buttons, rather
  you should set the `session_valid_configuration` flag for each of the buttons
  for whether or not the button *could* be enabled, then the session will
      handle whether or not a session can run based on if there is already
      something running.

### Clarifying the layout related codes

For display elements that will typically interact with the logical sections
should be declared with a typical field name. For pure layout-related display
elements, these elements should be prefixed with an underscore `_` when
decalring the field, and be constructed in a separate `__init_layout__` method.

### Decorators for GUI methods:

For various container methods that contain methods that is called on GUI signal
calls should be decorated with the `_QConatiner.gui_action` method, this
ensures that the GUI method does not hard crash when an error occurs (it will
throw a message) in the display panel. This makes it easier to debug what went
wrong.

