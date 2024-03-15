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
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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

        # Creating elements set by outer objects
        self.monitor_box = QGroupBox("Program monitor")
        self.gui_message = QLabel("")
        self.program_message = QLabel("")

        self.progress_bars = [
            # These need to be made in the main thread,
            # Should not need more than 6 progress bars in total???
            _QPBarContainer("", 0)
            for _ in range(6)
        ]

        # Additional flag for whether run-related buttons should be lock.
        # Buttons that should always check this flag is define as the
        # _QRunButton.
        self.run_lock: bool = False

        self.__init_layout__()
        self.__init_logger__()

    def __init_layout__(self):
        self._output_layout = QHBoxLayout()
        self._gui_msg_box = QGroupBox("GUI processing messages")
        self._gui_msg_box_layout = QHBoxLayout()
        self._gui_msg_box_layout.addWidget(self.gui_message)
        self._gui_msg_box.setLayout(self._gui_msg_box_layout)
        self._prog_msg_box = QGroupBox("Program messages")
        self._prog_msg_box_layout = QHBoxLayout()
        self._prog_msg_box_layout.addWidget(self.program_message)
        self._prog_msg_box.setLayout(self._prog_msg_box_layout)
        self._output_layout.addWidget(self._prog_msg_box)
        self._output_layout.addWidget(self._gui_msg_box)

        self._progress_layout = QVBoxLayout()
        for p in self.progress_bars:
            self._progress_layout.addWidget(p)
            p.hide()

        self._box_layout = QVBoxLayout()
        self._box_layout.addLayout(self._output_layout)
        self._box_layout.addLayout(self._progress_layout)
        self.monitor_box.setLayout(self._box_layout)

    def __init_logger__(self):
        # GUI Loggers
        gui_logger = logging.getLogger("GUI")
        gui_logger.addHandler(_QLabelHandler(self.gui_message))

        # Procedure logging methods
        prog_logger = logging.getLogger("QACProcedure")
        prog_logger.addHandler(_QLabelHandler(self.program_message))

    def refresh(self):
        """Forcing the update of children display elements"""

        def recursive_update(element: QWidget):
            """Recursively updating the various elements"""
            if hasattr(element, "_display_update"):
                element._display_update()
            for child in element.children():
                recursive_update(child)

        recursive_update(self)

    def recursive_set_lock(self, lock: Optional[bool] = None):
        """Locking all children display elements"""
        if lock is not None:
            self.run_lock = lock

        def _lock(element: QWidget):
            """Recursively updating the various elements"""
            if isinstance(element, _QRunButton):
                element._set_lock()
            for child in element.children():
                _lock(child)

        _lock(self)

    def iterate(self, x: Iterable, *args, **kwargs):
        """
        Iterating items to be reflected to the progress bar displays
        This part is currently broken... what should we do?
        """

        def _get_first_unused():
            for p in self.progress_bars:
                if not p.in_use:
                    return p

        p_item = _get_first_unused()
        p_item.in_use = True
        p_item.label.setText(kwargs.get("desc", "Process"))
        p_item.total = len(x)
        thread_tqdm = _QThreadableTQDM(x, *args, **kwargs)
        p_item.moveToThread(thread_tqdm.thread())
        p_item.show()
        thread_tqdm.progress.connect(p_item.progress)
        thread_tqdm.clear.connect(p_item.clear)
        return thread_tqdm


class _QLabelHandler(logging.Handler):
    """
    Have a label show the latest logging output.
    """

    def __init__(self, label: QLabel, level: int = logging.NOTSET):
        super().__init__(level=level)
        self._label = label

    def emit(self, record: logging.LogRecord):
        self._label.setText(record.msg)


class _QThreadableTQDM(QObject):
    start = pyqtSignal(int)
    progress = pyqtSignal(int)
    clear = pyqtSignal()

    def __init__(self, x: Iterable, *args, **kwargs):
        super().__init__()
        self._iterable = x
        self.start.emit(len(self._iterable))

    def __iter__(self):
        for idx, ret in enumerate(self._iterable):
            self.progress.emit(idx + 1)
            yield ret
        self.clear.emit()


class _QPBarContainer(QWidget):
    def __init__(self, name: str, total: int):
        # Cannot use non-text based updated.... what can we do about this?
        # Is a pseudo graphical method we can use???
        super().__init__()

        self._layout = QHBoxLayout()
        self.label = QLabel(name)
        self.pbar = QLabel("")
        self.total = total
        self._layout.addWidget(self.label, stretch=1)
        self._layout.addWidget(self.pbar, stretch=10)
        self.setLayout(self._layout)
        self.in_use = False

    def progress(self, x):
        self.pbar.setText(f"{x}/{self.total}")

    def clear(self):
        self.hide()
        self.in_use = False


class _QRunButton(QPushButton):

    def __init__(self, session: GUISession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

        # Other than the running flag, is the session correctly configured to
        # carry out this action? Default is to always set to be True
        self.session_config_valid = True

    def set_run(self, f: Callable, threaded=False):
        def _wrap(event):
            # Early return if this somehow slipped past run_lock
            if self.session.run_lock:
                self.setDisabled(True)
                return
            self.session.recursive_set_lock(True)  # Locking the button
            f()
            if not threaded:
                # Thread processes will need to be released by thread finish signals
                self.session.recursive_set_lock(False)

        self.clicked.connect(_wrap)

    def _display_update(self):
        if self.session.run_lock:
            self.setDisabled(True)
        else:
            self.setEnabled(self.session_config_valid)

    def _set_lock(self):
        self._display_update()


class _QContainer(QWidget):
    """
    Large containers which bundles chunks of information at a time. Exposing
    the parent instance with the name "session" for simpler exposing of
    hardware controls.
    """

    def __init__(self, session: GUISession):
        # NOTE: Because GUISession has multiple inheritance it must be setup
        # set this way??
        super().__init__()
        self.setParent(session)
        self.session = session  # Reference to main session instance

    @staticmethod
    def gui_action(f: Callable):
        """
        Common decorator for letting GUI action hit an error message instead of
        hard crashing.
        """

        @functools.wraps(f)
        def _wrap(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except Exception as err:
                logging.getLogger("GUI").error(str(err))

        return _wrap

    def _display_update(self):
        # By default, do nothing
        pass

    def log(self, s: str, level: int) -> None:
        logging.getLogger(f"GUI.{self.__class__.__name__}").log(
            level=level, msg=_str_(s)
        )

    def loginfo(self, s: str) -> None:
        self.log(s, logging.INFO)

    def logwarn(self, s: str) -> None:
        self.log(s, logging.WARNING)

    def logerror(self, s: str) -> None:
        self.log(s, logging.ERROR)


class _QLineEditDefault(QLineEdit):
    """Input method elements"""

    def __init__(self, default: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default = default
        self.setText(self._default)

    def revert_default(self):
        self.setText(self._default)


class _QSpinBoxDefault(QSpinBox):
    """Input method elements"""

    def __init__(self, default: int, min_value=0, max_value=99, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default = default
        self.setMinimum(min_value)
        self.setMaximum(max_value)
        self.setValue(self._default)

    def revert_default(self):
        self.setValue(self._default)


class _QComboPlaceholder(QComboBox):
    """Adding some pythonic methods to handling combo box methods"""

    def __init__(self, placeholder: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._placeholder = placeholder
        self.setEditable(True)
        self.setEditText("")
        self.lineEdit().setPlaceholderText(self._placeholder)

    def set_texts(self, texts: List[str]) -> None:
        self.clear()
        for t in texts:
            self.addItem(t)

    @property
    def item_texts(self):
        return [self.itemText(i) for i in range(self.count())]

    def on_textchange(self, f: Callable):
        """Short hand"""
        self.lineEdit().textChanged.connect(f)


class _QConfirmationDialog(QDialog):
    """
    Simple OK/Cancel confirmation box. The Ok/Cancel will return a simple
    True/False flag should something go wrong.
    """

    def __init__(self, parent, brief: str, full_message: str):
        super().__init__(parent)

        self.setWindowTitle(brief)
        self._buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._buttonBox.accepted.connect(self.accept)
        self._buttonBox.rejected.connect(self.reject)
        self._layout = QVBoxLayout()
        self._layout.addWidget(QLabel(_str_(full_message)))
        self._layout.addWidget(self._buttonBox)
        self.setLayout(self._layout)


def clear_layout(layout):
    """Clearing the contents of a Layout"""
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if isinstance(item.widget(), QWidget):
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())
            item.layout().deleteLater()
