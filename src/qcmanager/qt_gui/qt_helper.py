import functools
import logging
import time
from typing import Callable, Iterable, List, Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..utils import _str_
from .gui_session import GUISession


class _QContainer(QWidget):
    """
    Large containers which bundles chunks of information at a time. Exposing
    the parent instance with the name "session" for exposing hardware controls.
    """

    def __init__(self, session: GUISession):
        # NOTE: Because GUISession has multiple inheritance it must be setup
        # set this way
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
            self.recursive_set_lock(True)  # Locking the button
            f()
            if not threaded:
                # Thread processes will need to be released by thread finish
                # signals
                self.recursive_set_lock(False)

        self.clicked.connect(_wrap)

    def _display_update(self):
        if self.session.run_lock:
            self.setDisabled(True)
        else:
            self.setEnabled(self.session_config_valid)

    def _set_lock(self):
        self._display_update()

    def recursive_set_lock(self, lock: Optional[bool] = None):
        """Locking all children display elements"""
        if lock is not None:
            self.session.run_lock = lock

        def _lock(element: QWidget):
            """Recursively updating the various elements"""
            if isinstance(element, _QRunButton):
                element._set_lock()
            for child in element.children():
                _lock(child)

        _lock(self.session)


class _QLabelHandler(logging.Handler):
    """
    Have a label show the latest logging output.
    """

    def __init__(self, label: QLabel, level: int = logging.NOTSET):
        super().__init__(level=level)
        self.label = label

    def emit(self, record: logging.LogRecord):
        self.label.setText(record.msg)


class _QThreadableTQDM(QObject):
    progress = pyqtSignal(int)
    clear = pyqtSignal()

    def __init__(self, x: Iterable, *args, **kwargs):
        super().__init__()
        self._iterable = x

    def __iter__(self):
        for idx, ret in enumerate(self._iterable):
            self.progress.emit(idx + 1)
            yield ret
        self.clear.emit()


class _QPBarContainer(QWidget):
    def __init__(self, name: str, total: int):
        # Graphical update are prone to crashing when considering threading...
        # Hacking together a text-based display for progress instead
        super().__init__()

        # Display elements
        self.desc_label = QLabel(name)
        self.pbar_label = QLabel("")  # Using text based progress bar??
        self.frac_label = QLabel("")

        # Used to help with the display
        self.last_update = time.time()
        self.start_time = time.time()
        self.total = total
        self.in_use = False
        self._min_interval = 1 / 20.0
        self.__init_layout__()

    def __init_layout__(self):
        # No explicit layout would be added here. As the display elements would
        # most likely set want to be the set by the solution
        self.desc_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pbar_label.setStyleSheet("font-family: monospace")

    def pre_loop(self, name: str, total: int):
        self.total = total
        self.in_use = True
        self.last_update = time.time()
        self.start_time = time.time()
        self.desc_label.setText(name)
        self.desc_label.show()
        self.pbar_label.show()
        self.frac_label.show()

    def progress(self, x):
        if (time.time() - self.last_update) < self._min_interval and x != 1:
            return  # Early return if interval is too small
        current = time.time()
        # Updating the progress bar
        complete = int(100 * (x / self.total))
        remain = 100 - complete
        self.pbar_label.setText("[" + ("#" * complete) + ("-" * remain) + f"]")
        diff_time = current - self.start_time
        per_item = diff_time / x
        self.frac_label.setText(
            " ".join(
                [
                    f"[{x}/{self.total}]",
                    f"Total time: {diff_time:.1f}",
                    (
                        f"{1/per_item:.2f} it/sec"
                        if per_item < 0.1
                        else f"{per_item:.1f} sec/it"
                    ),
                ]
            )
        )

    def clear(self):
        self.in_use = False
        self.desc_label.hide()
        self.pbar_label.hide()
        self.frac_label.hide()
