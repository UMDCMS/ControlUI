import collections
import datetime
import logging
from typing import Dict, Iterable, List, Optional

import tqdm
from PyQt5.QtCore import QAbstractTableModel, QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...utils import timestampg
from ..gui_session import GUISession
from ..qt_helper import _QContainer


class _QPBarContainer(_QContainer):
    """
    Progress bar widget that can be used for object looping, like with TQDM.
    because we need the a QObject to generate signals, and QObject do not
    support multiple inheritance, we will create 2 helper classes:

        - _WrapTQDM for wrapping the extended TQDM object that can be used for
          iterating. Reusing TQDM methods ensures GUI design choices such as
          debouncing have been properly handled. Aside from the usual
          construction arguments that is passed to the TQDM instance, this will
          require a reference to the "signaller" class defined below
        - _QSignallerTQDM: for main object used to generate the pyqtSignals when
          iterating over a collection.
    """

    class _WrapTQDM(tqdm.tqdm):
        def __init__(self, signal, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._signal = signal

        def update(self, n=1):
            super().update(n)
            self._signal.progress.emit(self.n)

    class _QSignaller(QObject):
        progress = pyqtSignal(int)
        clear = pyqtSignal()

        def __init__(self, session: GUISession, x: Iterable, *args, **kwargs):
            super().__init__()
            self.tqdm_bar = _QPBarContainer._WrapTQDM(self, x, *args, **kwargs)
            # Add reference to main session object to capture the various signals
            self.session = session

        def __iter__(self):
            # main iteration class that is used to generate the signals. Mimicking
            # the structure and signal of the tqdm.std.__iter__ method:
            # See here:
            # https://github.com/tqdm/tqdm/blob/master/tqdm/std.py#L1160
            try:
                # Sending a zero signal to ensure that the display items are
                # properly refreshed
                self.progress.emit(0)
                for idx, x in enumerate(self.tqdm_bar):
                    if self.session.interupt_flag:
                        raise KeyboardInterrupt("Interupted by user!!")
                    yield x
            finally:
                self.clear.emit()

    def __init__(self, session: GUISession):
        super().__init__(session)

        # Display elements
        self.desc_label = QLabel("")
        self.pbar_widget = QProgressBar()
        # Item that stores the iteratable in TQDM
        self.tqdm: Optional[_QPBarContainer._WrapTQDM] = None
        self.signal_instance: Optional[_QPBarContainer._QSignaller] = None

    def __init_layout__(self):
        # No explicit layout would be added here. As the display elements would
        # most likely set want to be the set by the solution
        self.pbar_label.setStyleSheet("font-family: monospace")

    def prepare(self, x: Iterable, *args, **kwargs):
        self.in_use = True
        # Creating the signaller instance, and add reference to tqdm object
        self.signal_instance = _QPBarContainer._QSignaller(
            self.session, x, *args, **kwargs
        )
        self.tqdm = self.signal_instance.tqdm_bar

        # Setting the display elements to be visible
        self.desc_label.show()
        self.pbar_widget.show()
        self.desc_label.setText(self.tqdm.desc)
        self.pbar_widget.setMaximum(self.tqdm.total)

        # Connecting the signals to display element update
        self.signal_instance.progress.connect(self.progress)
        self.signal_instance.clear.connect(self.clear)

        # Returning the iterable signal object, as this is the object that is
        # used to generate the approprate signals.
        return self.signal_instance

    @_QContainer.gui_action
    def progress(self, x):
        self.pbar_widget.setValue(self.tqdm.n)

        # Getting the display text using the tqdm format bar
        format_dict = {k: v for k, v in self.tqdm.format_dict.items()}
        format_dict["ncols"] = 0  # Length 0 / stat only progress bar
        pbar_str = self.tqdm.format_meter(**format_dict)
        pbar_str = pbar_str[len(self.tqdm.desc) + 1 :]

        self.pbar_widget.setFormat(pbar_str)
        self.pbar_widget.setStyleSheet("font-family: monospace")

    def clear(self):
        self.in_use = False
        self.desc_label.hide()
        self.pbar_widget.hide()


class _QLabelHandler(logging.Handler):
    """
    Simpler handler for showing just the latest messages for specific types to
    targeted QLabels.
    """

    def __init__(
        self,
        info_label: Optional[QLabel] = None,
        warn_label: Optional[QLabel] = None,
        error_label: Optional[QLabel] = None,
        misc_label: Optional[QLabel] = None,
        level: int = logging.NOTSET,
    ):
        super().__init__(level=level)
        self.info_label = info_label
        self.warn_label = warn_label
        self.error_label = error_label
        self.misc_label = misc_label

        # Simple map to determine which display element to use
        self.__level_map__ = {
            logging.INFO: self.info_label,
            logging.WARN: self.warn_label,
            logging.ERROR: self.error_label,
        }

    def emit(self, record: logging.LogRecord):
        level = record.levelno
        label = None
        if level in self.__level_map__:
            label = self.__level_map__[level]
        if label is None:
            label = self.misc_label
        if label is not None:
            time_str = timestampg(datetime.datetime.fromtimestamp(record.created))
            label.setText(f"[{time_str}] {record.name}:{record.msg}")


class MemHandle(logging.Handler):
    """In-memory method for handling the various items"""

    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)
        self._log: Dict[int, Iterable[logging.LogRecord]] = {}

    def emit(self, record: logging.LogRecord):
        if record.levelno not in self._log:
            self._log[record.levelno] = collections.deque(maxlen=65536)
        self._log[record.levelno].append(record)


class SessionMessageDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        # Message box strictly related to GUI related items
        self.gui_message = QLabel("")

        # Messages for the main programs
        self.program_head = QLabel("<u>Program messages</u>")
        self.program_info = QLabel("")
        self.program_warn = QLabel("")
        self.program_error = QLabel("")
        self.program_misc = QLabel("")
        self.progress_bars: List[_QPBarContainer] = [
            _QPBarContainer(self.session) for _ in range(6)
        ]

        self.__init_layout__()
        self.__init_logger__()

    def __init_layout__(self):
        self._layout = QGridLayout()
        # FromRow/fromColumn/rowSpan/ColumnSpan
        self._layout.addWidget(self.program_head, 0, 0, 4, 1)
        #
        self._program_error_head = QLabel("Errors")
        self._layout.addWidget(self._program_error_head, 0, 1)
        self._layout.addWidget(self.program_error, 0, 2)
        self._program_error_head.setStyleSheet("background-color: red")

        self._program_warn_head = QLabel("Warnings")
        self._layout.addWidget(self._program_warn_head, 1, 1)
        self._layout.addWidget(self.program_warn, 1, 2)
        self._program_warn_head.setStyleSheet("background-color: orange")

        self._program_info_head = QLabel("Info.")
        self._layout.addWidget(self._program_info_head, 2, 1)
        self._layout.addWidget(self.program_info, 2, 2)
        self._program_info_head.setStyleSheet("background-color: green")

        self._program_misc_head = QLabel("Misc.")
        self._layout.addWidget(self._program_misc_head, 3, 1)
        self._layout.addWidget(self.program_misc, 3, 2)

        self._layout.addWidget(QLabel("GUI messages"), 4, 0)
        self._layout.addWidget(self.gui_message, 4, 1, 1, 2)

        for index, p in enumerate(self.progress_bars):
            self._layout.addWidget(p.desc_label, 5 + index, 0, 1, 2)
            self._layout.addWidget(p.pbar_widget, 5 + index, 1, 1, 2)
            p.clear()

        self._layout.setColumnStretch(0, 1)
        self._layout.setColumnStretch(1, 1)
        self._layout.setColumnStretch(2, 20)
        self.setLayout(self._layout)

    def __init_logger__(self):
        # GUI related messages
        gui_logger = logging.getLogger("GUI")
        gui_logger.addHandler(_QLabelHandler(misc_label=self.gui_message))

        # Procedure logging methods
        prog_logger = logging.getLogger("QACProcedure")

        prog_logger.addHandler(
            _QLabelHandler(
                info_label=self.program_info,
                warn_label=self.program_warn,
                error_label=self.program_error,
                misc_label=self.program_misc,
            )
        )
        self.memhandle = MemHandle()
        prog_logger.addHandler(self.memhandle)
        self.program_head.mousePressEvent = self.show_full_message_log

    def make_new_pcontainer(self) -> _QPBarContainer:
        p_item = _QPBarContainer(self.session)
        self._layout.addWidget(p_item.desc_label, 2 + len(self.progress_bars), 0)
        self._layout.addWidget(p_item.pbar_widget, 2 + len(self.progress_bars), 1)
        self.progress_bars.append(p_item)
        return self.progress_bars[-1]

    def iterate(self, x: Iterable, *args, **kwargs):
        """
        The progress bar containers cannot be initialized here due to import
        restrictions. The main constructer must make sure that the main session
        Qwidget points to this class method
        """

        def _get_first_unused() -> _QPBarContainer:
            for p in self.progress_bars:
                if not p.in_use:
                    return p
            return self.make_new_pcontainer()

        p_item = _get_first_unused()
        return p_item.prepare(x, *args, **kwargs)

    def show_full_message_log(self, event=None):
        dialog = _QLogDisplay(self.memhandle._log)
        dialog.exec()


class _QLogDisplay(QDialog):
    class LogTableModel(QAbstractTableModel):
        @classmethod
        def make_single(cls, record: logging.LogRecord):
            return [
                record.name.replace("QCAProcedure.", ""),
                timestampg(datetime.datetime.fromtimestamp(record.created)),
                record.levelno,  # Better parsing?
                record.msg,
            ]

        def __init__(self, log_entries: Dict[int, Iterable[logging.LogRecord]]):
            super().__init__()
            self._table = []  # Saving entry as plain list
            for level in sorted(log_entries.keys(), reverse=True):
                self._table.extend(
                    [self.make_single(x) for x in reversed(log_entries[level])]
                )

        def data(self, index, role):
            if role == Qt.DisplayRole:
                return self._table[index.row()][index.column()]

        def headerData(self, section, orientation, role):
            # section is the index of the column/row.
            if role == Qt.DisplayRole:
                if orientation == Qt.Horizontal:
                    if section == 0:
                        return "Name"
                    if section == 1:
                        return "Time"
                    if section == 2:
                        return "Entry Level"
                    if section == 3:
                        return "Message"
                    return ""

                if orientation == Qt.Vertical:
                    return section

        def rowCount(self, index):
            return len(self._table)

        def columnCount(self, index):
            return 4  # We should allow this to dynamically change??

    def __init__(self, log_entries=Dict[int, Iterable[logging.LogRecord]]):
        super().__init__()
        self.table = QTableView()
        self.model = _QLogDisplay.LogTableModel(log_entries)
        self.table.setModel(self.model)
        self.__init_layout__()

    def __init_layout__(self):
        self.setWindowTitle("Full message Log display")
        self._layout = QVBoxLayout()
        self._layout.addWidget(self.table)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setLayout(self._layout)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
