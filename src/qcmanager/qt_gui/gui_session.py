from typing import Iterable, Optional

from PyQt5.QtWidgets import QWidget

from ..session import Session


class GUISession(Session):
    """
    Extended session object, as interactions with the GUI will require slight
    modifications to how the interfaces are handled. This will also contain the
    outermost widget to be used by the application window.
    """

    def __init__(self):
        super().__init__()

        # Additional flag for whether run-related buttons should be lock.
        # Buttons that should always check this flag is define as the
        # _QRunButton.
        self.run_lock: bool = False

        # Addtional flag to indicate whether a process should be terminated by
        # a user interruption signal
        self.interupt_flag: bool = False

        # Object as the main window
        self.main_container = QWidget()

        # Reference to the container that will be responsible for holding the
        # messages an progress bars, will need to be handle the layout
        # initialization methods
        self.message_container = None

    def iterate(self, x: Iterable, *args, **kwargs):
        """
        The progress bar containers cannot be initialized here due to import
        restrictions. The main constructer must make sure that the correct
        handler for the message container is passed to the object
        """
        assert self.message_container is not None, "Message container not initialized"
        return self.message_container.iterate(x, *args, **kwargs)

    """
    Full interface update methods. Use sparingly, as these maybe expensive. We
    cannot import the helper widget/containers here, so we will simply have to
    point to the custom methods that we have created.
    """

    def refresh(self):
        """
        Forcing the update of children display elements. All elements that
        requires refreshing should implement a `_display_update` method.
        """

        def recursive_update(element: QWidget):
            """Recursively updating the various elements"""
            if hasattr(element, "_display_update"):
                element._display_update()
            for child in element.children():
                recursive_update(child)

        recursive_update(self.main_container)

    def lock_buttons(self, lock: Optional[bool] = None):
        """
        Setting disable flags for all the various buttons in the interface.
        Button elements should implement the `_set_lock` method.
        """
        if lock is not None:
            self.run_lock = lock

        def recursive_lock(element: QWidget):
            """Recursively updating the various elements"""
            if hasattr(element, "_set_lock"):
                element._set_lock()
            for child in element.children():
                recursive_lock(child)

        recursive_lock(self.main_container)
