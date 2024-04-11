import collections
import datetime
import logging
from typing import Dict, Iterable, List, Optional

import tqdm
from PyQt5.QtCore import QAbstractTableModel, QObject, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
)

from ...utils import timestampg
from ..gui_session import GUISession
from ..qt_helper import _QContainer


class _QSignalTQDM(QObject):
    """
    A TQDM wrapper that can emit and receive pyqt signals. Because these
    objects will need to be spawned in separate threads, this object is written
    as a standalone object without any ties to display elements. The display
    elements will need to connect with the various iterating signals.
    """

    progress = pyqtSignal(int)
    clear = pyqtSignal()

    class _WrapTQDM(tqdm.tqdm):
        def __init__(self, signal, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._signal = signal

        def update(self, n=1):
            super().update(n)
            self._signal.progress.emit(self.n)

        """
        Disabling the CLI display function, to not litter the command line
        output
        """

        def refresh(self, no_lock=False, lock_args=None):
            return

        def close(self):
            return

    def __init__(self, session: GUISession, x: Iterable, *args, **kwargs):
        super().__init__()
        self.tqdm_bar = _QSignalTQDM._WrapTQDM(self, x, *args, **kwargs)
        # Additional flag to allow for interupt signals
        self.interupt: bool = False
        # Setting the signal connection
        self.session = session
        self.session.interupt_signal.connect(self.receive_interupt)

    def __iter__(self):
        # main iteration class that is used to generate the signals. Mimicking
        # the structure and signal of the tqdm.std.__iter__ method:
        # See here:
        # https://github.com/tqdm/tqdm/blob/master/tqdm/std.py#L1160
        try:
            # Sending a zero signal to ensure that the display items are
            # properly refreshed
            self.progress.emit(0)
            for x in self.tqdm_bar:
                if self.session.interupt_flag:
                    raise KeyboardInterrupt("Interupted by user!!")
                yield x
            # Sedding final signal at the end of the loop
            self.progress.emit(self.tqdm_bar.total)
        finally:
            self.clear.emit()

    # This method does not work??? WHY??
    def receive_interupt(self):
        print("Recieved interupt signal!!!")
        self.interupt = True


class _QPBarHandler:
    """
    Display elements of the a wrapped TQDM object. Because the TQDM instances
    are expected to be ran in a separate thread, the iterate method should not
    be attached to the main containers. So we need to expose the iterate method
    as a series of callable objects. Here expose one of such callable objects.
    For some reason, the graphical QProgressBar object has many issues with
    threading, here we are going to use a text-based display of the progress
    bar as a work around. (Can we properly fix this??)
    """

    def __init__(self, session: GUISession, foreground="#8888FF", background="#888888"):
        # For global signal parsing
        self.session = session
        # Display elements - These should be initialized elsewhere to ensure
        # that they can be passed around different threads
        self.desc_label = QLabel("")
        self.progress_bar = QLabel("")
        self.stat_label = QLabel("")
        self.foreground = foreground
        self.background = background
        # Pointer objects to the signals generators
        self.signal: Optional[_QSignalTQDM] = None
        self.tqdm: Optional[_QSignalTQDM._WrapTQDM] = None
        self.clear()

    def connect(self, signal: _QSignalTQDM):
        """
        Call method for spawning in the tqdm instance, also connecting the
        various signal instances, for the spawned in instance
        """
        self.signal = signal
        self.tqdm = self.signal.tqdm_bar

        # Initial setups
        self.desc_label.setText(self.tqdm.desc)
        self.desc_label.setFont(self.make_font())
        self.progress_bar.setText("")
        self.progress_bar.setFont(self.make_font())
        self.progress_bar.setAlignment(Qt.AlignCenter)

        self.stat_label.setText("")
        self.stat_label.setFont(self.make_font())

        # Iterative update signals
        self.signal.progress.connect(self.progress)
        self.signal.clear.connect(self.clear)

        # General update
        self.session.interupt_signal.connect(self.signal.receive_interupt)

    @_QContainer.gui_action
    def progress(self, n: int):
        # Setting the main graphical elements
        format_dict = {k: v for k, v in self.tqdm.format_dict.items()}
        format_dict["ncols"] = 0  # Length 0 for only stat bar
        format_dict["prefix"] = ""
        self.stat_label.setText(self.tqdm.format_meter(**format_dict))

        # Setting up the gradient style sheel
        percent = n / self.tqdm.total
        template = "background: qlineargradient(x1:0, x2:1, {stops})"
        stops = [(0, self.foreground), (percent, self.foreground), (1, self.background)]
        if percent != 1:
            stops.insert(2, (percent + 0.000001, self.background))
        cast = lambda x: f"stop: {x[0]} {x[1]}"
        sheet = template.format(stops=",".join([cast(x) for x in stops]))
        self.progress_bar.setStyleSheet(sheet)
        self.progress_bar.setText(f"{n}/{self.tqdm.total}  [{percent*100:.1f}%]")

    @_QContainer.gui_action
    def clear(self):
        # Hiding the various display elements
        self.desc_label.setText("")
        self.desc_label.setFont(self.make_font(size=1))
        self.progress_bar.setText("")
        self.progress_bar.setFont(self.make_font(size=1))
        self.progress_bar.setStyleSheet("")
        self.stat_label.setText("")
        self.stat_label.setFont(self.make_font(size=1))
        self.stat_label.setStyleSheet("")
        if self.signal is not None:
            self.signal.progress.disconnect()
            self.signal.clear.disconnect()
            self.signal.deleteLater()
            self.signal = None

    @classmethod
    def make_font(cls, size=None):
        font = QFont("Sans Serif")
        if size is not None:
            font.setPointSize(size)
        return font

    @property
    def in_use(self):
        return self.signal is not None


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

        self.progress_handlers: List[_QPBarHandler] = [
            _QPBarHandler(self.session) for _ in range(6)
        ]  # Will never need for than 6 progress bars?

        self.__init_layout__()
        self.__init_logger__()

    def __init_layout__(self):
        self._layout = QGridLayout()
        # FromRow/fromColumn/rowSpan/ColumnSpan
        self._layout.addWidget(self.program_head, 0, 0, 4, 1)
        #
        self._program_error_head = QLabel("Errors")
        self._layout.addWidget(self._program_error_head, 0, 1)
        self._layout.addWidget(self.program_error, 0, 2, 1, 2)
        self._program_error_head.setStyleSheet("background-color: red")
        self.program_error.setWordWrap(True)

        self._program_warn_head = QLabel("Warnings")
        self._layout.addWidget(self._program_warn_head, 1, 1)
        self._layout.addWidget(self.program_warn, 1, 2, 1, 2)
        self._program_warn_head.setStyleSheet("background-color: orange")
        self.program_warn.setWordWrap(True)

        self._program_info_head = QLabel("Info.")
        self._layout.addWidget(self._program_info_head, 2, 1)
        self._layout.addWidget(self.program_info, 2, 2, 1, 2)
        self._program_info_head.setStyleSheet("background-color: green")
        self.program_info.setWordWrap(True)

        self._program_misc_head = QLabel("Misc.")
        self._layout.addWidget(self._program_misc_head, 3, 1)
        self._layout.addWidget(self.program_misc, 3, 2, 1, 2)
        self.program_misc.setWordWrap(True)

        self._layout.addWidget(QLabel("GUI messages"), 4, 0)
        self._layout.addWidget(self.gui_message, 4, 1, 1, 3)

        for index, p in enumerate(self.progress_handlers):
            self._layout.addWidget(p.desc_label, 5 + index, 0, 1, 2)
            self._layout.addWidget(p.progress_bar, 5 + index, 1, 1, 2)
            self._layout.addWidget(p.stat_label, 5 + index, 3, 1, 1)
            p.clear()

        self._layout.setColumnStretch(0, 2)  # Header
        self._layout.setColumnStretch(1, 1)  # Message header
        self._layout.setColumnStretch(2, 8)  # Main content
        self._layout.setColumnStretch(3, 3)  # Progress bar hea
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

    def iterate(self, iterable, *args, **kwargs):
        """
        Returning the first progress bar handler that is currently not being used
        """
        tqdm_instance = _QSignalTQDM(self.session, iterable, *args, **kwargs)

        for handler in self.progress_handlers:
            if not handler.in_use:
                handler.connect(tqdm_instance)
                break
        # TODO: What should be done if more than 6 progress bars are spawned??
        return tqdm_instance

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
