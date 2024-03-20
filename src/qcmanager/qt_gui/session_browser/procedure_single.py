import time
from typing import Dict, Type

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ... import procedures
from ...procedures import _parsing as proc_parsing
from ...procedures._procedure_base import ProcedureBase
from ...utils import _str_
from ..gui_session import GUISession
from ..qt_helper import _QContainer, _QLineEditDefault, _QRunButton, _QSpinBoxDefault


class Worker(QObject):
    """
    Helper object to run processes in the background. Otherwise all GUI
    elements would be locked is not locked
    """

    finished = pyqtSignal()

    def __init__(
        self,
        session: GUISession,
        procedure_class: ProcedureBase,
        procedure_arguments=Dict[str, any],
    ):
        super().__init__()
        self.session = session
        self.procedure_class = procedure_class
        self.procedure_arguments = procedure_arguments

    def run(self):
        time.sleep(0.1)  # Adding artificial delay
        self.session.handle_procedure(
            self.procedure_class,
            procedure_arguments=self.procedure_arguments,
        )
        time.sleep(0.1)  # Adding artificial delay
        self.finished.emit()


class SingleProcedureTab(_QContainer):
    N_COLUMNS = 3

    def __init__(self, session: GUISession, procedure_class: Type):
        super().__init__(session)
        self.procedure_class = procedure_class

        # A map of the procedures argument names to a tuple of
        # - type of variable
        # - the QWidget used to handle the input
        # - the parameter object for general search
        self.input_map = {}
        for index, (name, param) in enumerate(
            proc_parsing.get_procedure_args(procedure_class).items()
        ):
            self.input_map[name] = (
                proc_parsing.get_param_type(param),
                SingleProcedureTab.create_param_input(param),
                param,
            )

        # Buttons for users to press
        self.run_button = _QRunButton(self.session, f"Run {procedure_class.__name__}")
        self.run_button.set_run(self.run_procedure, threaded=True)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.revert_default)

        self.__init_layout__()
        self._display_update()

    def _display_update(self):
        self.run_button.session_config_valid = (
            self.session.board_id != "" or self.session.board_type != ""
        )

    def __init_layout__(self):
        self._outer_layout = QHBoxLayout()
        self.setLayout(self._outer_layout)
        self._doc_label = QLabel(_str_(self.procedure_class.__doc__))
        self._doc_label.setWordWrap(True)
        self._outer_layout.addWidget(self._doc_label)
        self._inputs = QVBoxLayout()
        self._outer_layout.addLayout(self._inputs)
        self._grid = QGridLayout()
        self._inputs.addLayout(self._grid)

        # Inserting input elements into grid layout
        for index, (name, (param_type, param_input, param)) in enumerate(
            self.input_map.items()
        ):
            param_label = QLabel(name)
            param_label.setToolTip(proc_parsing.get_param_doc(param))
            column = index % SingleProcedureTab.N_COLUMNS
            row = index // SingleProcedureTab.N_COLUMNS
            self._grid.addWidget(param_label, row, column * 3, Qt.AlignRight)
            self._grid.addWidget(param_input, row, column * 3 + 1)

        # Additional spacing settings
        for idx in range(self._grid.columnCount()):
            if idx % 3 == 2:
                self._grid.setColumnStretch(idx, 1)
            else:
                self._grid.setColumnStretch(idx, 10)
        # Adding the run button
        self._button_layout = QHBoxLayout()
        self._button_layout.addWidget(self.run_button)
        self._button_layout.addWidget(self.clear_button)
        self._inputs.addLayout(self._button_layout)

    def run_procedure(self):
        """Running the procedure in a separate thread"""
        self._worker = Worker(
            self.session,
            self.procedure_class,
            procedure_arguments={
                name: t(i.text()) for name, (t, i, p) in self.input_map.items()
            },
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)

        # Additional tiems to run after thread has completed
        self._thread.finished.connect(lambda: self.loginfo("Completed running!!"))
        self._thread.finished.connect(lambda: self.run_button.recursive_set_lock(False))
        self._thread.finished.connect(lambda: self.session.refresh())
        self._thread.finished.connect(self._thread.deleteLater)
        # Starting the main thread
        self._thread.start()

    def revert_default(self):
        for t, input_widget in self.input_map.values():
            if hasattr(input_widget, "revert_default"):
                input_widget.revert_default()

    @staticmethod
    def create_param_input(param: proc_parsing.inspect.Parameter) -> QWidget:
        param_type = proc_parsing.get_param_type(param)
        if param_type is float:
            if proc_parsing.has_default(param):
                return _QLineEditDefault(str(param.default))
            return QLineEdit()
        if param_type is int:
            if proc_parsing.has_default(param):
                return _QSpinBoxDefault(
                    param.default, min_value=-999999, max_value=99999
                )
            return _QSpinBoxDefault(0, min_value=-999999, max_value=99999)
        return QLineEdit()


class SessionRunSingleProcedure(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self._outer = QVBoxLayout()
        self._box = QGroupBox("Run single procedure")
        self._inner = QHBoxLayout()
        self._box.setLayout(self._inner)
        self._outer.addWidget(self._box)
        self.setLayout(self._outer)

        self._tabs = QTabWidget()

        for method_class in procedures.__all_procedures__:
            self._tabs.addTab(
                SingleProcedureTab(self.session, method_class), method_class.__name__
            )
        self._inner.addWidget(self._tabs)
