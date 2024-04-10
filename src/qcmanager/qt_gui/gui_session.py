from typing import Iterable, Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from ..session import Session


class GUISession(Session, QWidget):
    """
    Extended session object, as interactions with the GUI will require slight
    modifications to how the interfaces are handled. This will also contain the
    outermost widget to be used by the application window.
    """

    # Global signals to ensure that display elements can be updated from any
    # where. Use sparingly!
    button_lock_signal = pyqtSignal(bool)
    refresh_signal = pyqtSignal()

    def __init__(self):
        # Single super initialization does not work well with multiple
        # inherience of QObjects
        Session.__init__(self)
        QWidget.__init__(self)

        # Additional flag for whether run-related buttons should be lock.
        # Buttons that should always check this flag is define as the
        # _QRunButton.
        self.run_lock: bool = False

        # Addtional flag to indicate whether a process should be terminated by
        # a user interruption signal
        self.interupt_flag: bool = False

        # Reference to the container that will be responsible for holding the
        # messages an progress bars, will need to be handle the layout
        # intialization methods
        self.message_container = None

        def _update_lock(x: bool):
            self.run_lock = x

        self.button_lock_signal.connect(_update_lock)

    def iterate(self, x: Iterable, *args, **kwargs):
        """
        The progress bar containers cannot be initialized here due to import
        restrictions. The main constructer must make sure that the correct
        handler for the message container is passed to the object
        """
        assert self.message_container is not None, "Message container not initialized"
        return self.message_container.iterate(x, *args, **kwargs)
