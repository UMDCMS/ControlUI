import logging
from typing import Iterable, List

import tqdm
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QGridLayout, QGroupBox, QLabel, QProgressBar, QWidget

from ..gui_session import GUISession
from ..qt_helper import _QContainer, _QLabelHandler


class _QThreadableTQDM(QObject):
    # A threadable loop object. As we cannot have multiple inheritance with
    # QObjects, we will create a tqdm object to use as styling of the object.
    # We will still use the underlying TQDM object to help with styling and
    # avoiding excessive signal generation
    progress = pyqtSignal(int)
    clear = pyqtSignal()

    class _WrapTQDM(tqdm.tqdm):
        # Thin wrapper to automatically handle the emit progress signal
        def __init__(self, obj, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._parent = obj

        def update(self, n=1):
            super().update(n)
            self._parent.progress.emit(self.n)

    def __init__(self, session: GUISession, x: Iterable, *args, **kwargs):
        super().__init__()
        self.tqdm_bar = _QThreadableTQDM._WrapTQDM(self, x, *args, **kwargs)
        # Add reference to main session object to capture the various signals
        self.session = session

    def __iter__(self):
        # main iteration class that is used to generate the signals. Mimicking
        # the structure and signal of the tqdm.std.__iter__ method:
        # See here:
        # https://github.com/tqdm/tqdm/blob/master/tqdm/std.py#L1160
        try:
            for x in self.tqdm_bar:
                if self.session.interupt_flag:
                    raise KeyboardInterrupt("Interupted by user!!")
                yield x
        finally:
            self.clear.emit()


class _QPBarContainer(QWidget):
    def __init__(self):
        super().__init__()

        # Display elements
        self.desc_label = QLabel("")
        self.pbar_widget = QProgressBar()
        self.tqdm_instance: _QThreadableTQDM._WrapTQDM = None

    def __init_layout__(self):
        # No explicit layout would be added here. As the display elements would
        # most likely set want to be the set by the solution
        self.pbar_label.setStyleSheet("font-family: monospace")

    def prepare(self, instance: _QThreadableTQDM._WrapTQDM):
        # Wrapping the instances
        self.in_use = True
        self.tqdm_instance = instance

        # Setting the display elements to be visible
        self.desc_label.show()
        self.pbar_widget.show()
        self.desc_label.setText(self.tqdm_instance.tqdm_bar.desc)
        self.pbar_widget.setMaximum(self.tqdm_instance.tqdm_bar.total)

        # Connecting the signals to display element update
        self.tqdm_instance.progress.connect(self.progress)
        self.tqdm_instance.clear.connect(self.clear)

    @_QContainer.gui_action
    def progress(self, x):
        tqdm_bar = self.tqdm_instance.tqdm_bar
        desc = tqdm_bar.desc

        self.pbar_widget.setValue(tqdm_bar.n)

        # Getting the display text using the tqdm format bar
        format_dict = {k: v for k, v in tqdm_bar.format_dict.items()}
        format_dict["ncols"] = 0  # Length 0 / stat only progress bar
        pbar_str = tqdm_bar.format_meter(**format_dict)
        pbar_str = pbar_str[len(desc) + 1 :]

        self.pbar_widget.setFormat(pbar_str)
        self.pbar_widget.setStyleSheet("font-family: monospace")

    def clear(self):
        self.in_use = False
        self.desc_label.hide()
        self.pbar_widget.hide()


class SessionMessageDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        # Creating elements set by outer objects
        self.monitor_box = QGroupBox("Program monitor")
        self.gui_message = QLabel("")
        self.program_message = QLabel("")
        self.progress_bars: List[_QPBarContainer] = [
            _QPBarContainer() for _ in range(6)
        ]

        self.__init_layout__()
        self.__init_logger__()

    def __init_layout__(self):
        self._layout = QGridLayout()
        self._layout.addWidget(QLabel("Program messages"), 0, 0)
        self._layout.addWidget(self.program_message, 0, 1)

        self._layout.addWidget(QLabel("GUI messages"), 1, 0)
        self._layout.addWidget(self.program_message, 1, 1)

        for index, p in enumerate(self.progress_bars):
            self._layout.addWidget(p.desc_label, 2 + index, 0)
            self._layout.addWidget(p.pbar_widget, 2 + index, 1)
            p.clear()

        self._layout.setColumnStretch(0, 1)
        self._layout.setColumnStretch(1, 20)
        self.setLayout(self._layout)

    def __init_logger__(self):
        # GUI Loggers
        gui_logger = logging.getLogger("GUI")
        gui_logger.addHandler(_QLabelHandler(self.gui_message))

        # Procedure logging methods
        prog_logger = logging.getLogger("QACProcedure")
        prog_logger.addHandler(_QLabelHandler(self.program_message))

    def make_new_pcontainer(self) -> _QPBarContainer:
        p_item = _QPBarContainer()
        self._layout.addWidget(p_item.desc_label, 2 + len(self.progress_bars), 0)
        self._layout.addWidget(p_item.pbar_widget, 2 + len(self.progress_bars), 1)
        self.progress_bars.append(p_item)
        return self.progress_bars[-1]

    def iterate(self, x: Iterable, *args, **kwargs):
        """
        The progress bar containers cannot be initialized here due to import
        restrictions. The main constructer must make sure that a new session
        """

        def _get_first_unused() -> _QPBarContainer:
            for p in self.progress_bars:
                if not p.in_use:
                    return p
            # If everything is in use, spawn a new item
            return self.make_new_pcontainer()

        p_item = _get_first_unused()
        p_item.prepare(_QThreadableTQDM(self.session, x, *args, **kwargs))
        return p_item.tqdm_instance
