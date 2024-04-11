import functools
import logging
import time
import traceback
from typing import Callable, List

from PyQt5.QtCore import QMetaMethod, QObject
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..utils import _str_
from .gui_session import GUISession


def clear_layout(layout):
    """
    Clearing the container contents of a layout. As this operation is
    potentially expensive, use this method sparingly!
    """
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if isinstance(item.widget(), QWidget):
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())
            item.layout().deleteLater()


def get_signal(obj: QObject, signal_name: str):
    """
    Getting the signal object associated to a QObject by the signal name
    """
    for i in range(obj.metaObject().methodCount()):
        meta_method = obj.metaObject().method(i)
        if not meta_method.isValid():
            continue
        if (
            meta_method.methodType() == QMetaMethod.Signal
            and meta_method.name() == signal_name
        ):
            return meta_method


class _QContainer(QWidget):
    """
    Large containers which bundles chunks of information at a time. Exposing
    the parent instance with the name "session" for exposing hardware controls.
    """

    def __init__(self, session: GUISession):
        # NOTE: Because GUISession has multiple inheritance it must be setup
        # set this way
        super().__init__()
        self.session = session  # Reference to main session instance

        # On refresh signals, this wrapper methods ensures that there will not
        # be multiple refreshs being called to the same object. Subsequent
        # methods should overload the self._display_update method
        self._refresh_lock = False
        self.session.refresh_signal.connect(self.__display_update_debounce)

        self.session.refresh_signal.connect(self._display_update)

    @staticmethod
    def gui_action(f: Callable):
        """
        Common decorator for letting GUI action create an error message instead
        of hard crashing. Helps with debugging the information.
        """

        @functools.wraps(f)
        def _wrap(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except Exception as err:
                print(traceback.format_exc())
                logging.getLogger("GUI").error(str(err))

        return _wrap

    def __display_update_debounce(self):
        while self._refresh_lock is True:
            time.sleep(0.01)  # 1ms intervals should be fast enough

        self._refresh_lock = True
        try:
            self._display_update()
        finally:
            # Regardless of whether the display update is sucessful, always release the lock
            self._refresh_lock = False

    def _display_update(self):
        """
        Method to overload to define what should be done when a refresh
        signal is requested by the user. By default do nothing.
        """
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


class _QDoubleSpinBoxDefault(QDoubleSpinBox):
    def __init__(
        self, default: float, min_value=0, max_value=99, precision=3, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._default = default
        self.setMinimum(min_value)
        self.setMaximum(max_value)
        self.setDecimals(precision)
        self.setSingleStep(10 ** (-precision))
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

    def revert_default(self):
        self.lineEdit().setText("")


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


class _QRunButton(QPushButton):
    """
    Button that handles the locking of other buttons when clicked. See the
    set_lock method in the main session handle
    """

    def __init__(self, session: GUISession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

        # Other than the running flag, is the session correctly configured to
        # carry out this action? Default is to always set to be True
        self.session_config_valid = True
        self.session.button_lock_signal.connect(self._set_lock)

    def run_connect(self, run_call: Callable, threaded=False):
        """
        Additional wrapper the callable action which ensures that the interface
        is properly locked the the run call is created. The threaded flag is
        used to indicate that the callable method will spawn a thread in a
        separate method and thus should not unlock the buttons when the method
        terminates.
        """

        def _wrap(event):
            if self.session.run_lock:
                self.setDisabled(True)
                return
            # Locking buttons and releasing if not a threaded method
            self.session.button_lock_signal.emit(True)
            self.session.interupt_flag = False
            run_call()
            if not threaded:
                self._post_run()

        self.clicked.connect(_wrap)

    def _post_run(self):
        self.session.interupt_flag = False  # Always try to release the flag
        self.session.button_lock_signal.emit(False)
        self.session.refresh_signal.emit()

    def _display_update(self):
        self._set_lock(self.session.run_lock)

    def _set_lock(self, lock_status):
        if lock_status is True:
            self.setDisabled(True)
        else:
            self.setEnabled(self.session_config_valid)
