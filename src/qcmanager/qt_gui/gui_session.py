"""
The contents is exclusively create to add additional interface wrappers that
would be suitable for the GUI. The main layout of the GUI elements will be
handled in create_default_session method define in the __init__.py file
"""

import functools
import logging
import time
from typing import Callable, Iterable, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget

# Loading in the main session object for handling the various instances
from ..session import Session
from ..utils import _str_

"""

Helper classes for nicer interface to create GUI elements

"""


class GUISession(Session, QWidget):
    # Main window that is also the session instance
    def __init__(self):
        Session.__init__(self)
        QWidget.__init__(self)

        # Additional flag for whether run-related buttons should be lock.
        # Buttons that should always check this flag is define as the
        # _QRunButton.
        self.run_lock: bool = False

        # Reference to the container that will be responsible for holding the
        # messages an progress bars, will need to be handle the initial layout
        # methods
        self.message_container = None

    def refresh(self):
        """Forcing the update of children display elements"""

        def recursive_update(element: QWidget):
            """Recursively updating the various elements"""
            if hasattr(element, "_display_update"):
                element._display_update()
            for child in element.children():
                recursive_update(child)

        recursive_update(self)

    def iterate(self, x: Iterable, *args, **kwargs):
        """
        The progress bar containers cannot be initialized here due to import
        restrictions. The main constructer must make sure that a new session
        """
        assert self.message_container is not None, "Message container not initialized"
        return self.message_container.iterate(x, *args, **kwargs)
