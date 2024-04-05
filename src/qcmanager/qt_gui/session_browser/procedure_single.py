import inspect
from typing import Any, Dict, Type

from PyQt5.QtCore import Qt, QThread
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

from ... import procedures, run_single_procedure
from ...procedures import _argument_validation as arg_validation
from ...procedures import _parsing as proc_parsing
from ...utils import _str_
from ..gui_session import GUISession
from ..qt_helper import (
    _QComboPlaceholder,
    _QContainer,
    _QDoubleSpinBoxDefault,
    _QInteruptButton,
    _QLineEditDefault,
    _QRunButton,
    _QSpinBoxDefault,
)


class SingleProcedureThread(QThread):
    """
    Wrapper around `run_single_procedure` to a QThread object to allow it to be
    ran in the background. This allows for display elements to be continuously
    updated, while the process is still running.
    """

    def __init__(
        self,
        session: GUISession,
        procedure_class: Type,
        procedure_arguments=Dict[str, any],
    ):
        super().__init__()
        self.session = session
        self.procedure_class = procedure_class
        self.procedure_arguments = procedure_arguments

    def run(self):
        run_single_procedure(
            self.session,
            self.procedure_class,
            procedure_arguments=self.procedure_arguments,
        )


class SingleProcedureTab(_QContainer):
    """
    The tab containing the setting up the various input fields to place for
    runing a singular defined procedure class.
    """

    N_COLUMNS = 3

    def __init__(self, session: GUISession, procedure_class: Type):
        super().__init__(session)
        self.procedure_class = procedure_class

        # A map of the procedures argument names to a tuple of
        # - type of variable
        # - the QWidget used to handle the input
        # - the parameter object for general search
        # For construction of such items, see the build_input_widgets method
        self.input_map = {}

        # Buttons for users to press
        self.run_button = _QRunButton(
            self.session, f"Run {self.procedure_class.__name__}"
        )
        self.run_button.run_connect(self.run_procedure, threaded=True)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.revert_default)

        self.__init_layout__()
        self._display_update()

    def _display_update(self):
        # Run button must only be enabled if the session is actually loaded
        self.run_button.session_config_valid = (
            self.session.board_id != "" or self.session.board_type != ""
        )
        # TODO: disable button if hardware requirements are not met?

        # Rebuild every time a refresh is requested as the inputs may contain
        # session-dependent variables
        self.build_input_widget()

    def __init_layout__(self):
        self._doc_label = QLabel(_str_(self.procedure_class.__doc__))
        self._doc_label.setWordWrap(True)
        self._inputs = QVBoxLayout()
        self._grid = QGridLayout()
        self._inputs.addLayout(self._grid)

        self._button_layout = QHBoxLayout()
        self._button_layout.addWidget(self.run_button)
        self._button_layout.addWidget(self.clear_button)
        self._inputs.addLayout(self._button_layout)

        self._outer_layout = QHBoxLayout()
        self._outer_layout.addWidget(self._doc_label, stretch=1)
        self._outer_layout.addLayout(self._inputs, stretch=2)
        self.setLayout(self._outer_layout)

    def run_procedure(self):
        """Running the procedure in a separate thread"""
        self._thread = SingleProcedureThread(
            self.session,
            self.procedure_class,
            procedure_arguments={
                name: self.cast_widget_input(t, i, p)
                for name, (t, i, p) in self.input_map.items()
            },
        )
        # Additional items to run after thread has completed
        self._thread.finished.connect(self._post_procedure)
        self._thread.finished.connect(self._thread.deleteLater)
        # Starting the execution thread
        self._thread.start()

    def _post_procedure(self):
        self.loginfo(f"Completed running {self.procedure_class.__name__}")
        self.session.lock_buttons(False)
        # Clean up to ensure that all in-use items are cleaned up
        self.session.interupt_flag = False
        for pbar in self.session.message_container.progress_bars:
            pbar.clear()
        self.session.refresh()

    def revert_default(self):
        for _, input_widget, __ in self.input_map.values():
            if hasattr(input_widget, "revert_default"):
                input_widget.revert_default()

    def build_input_widget(self):
        # Making sure to clear the inputs first
        for _, input_widget, __ in self.input_map.values():
            input_widget.deleteLater()
        self.input_map = {}

        # Creating the fresh itesm
        for name, param in proc_parsing.get_procedure_args(
            self.procedure_class
        ).items():
            self.input_map[name] = (
                proc_parsing.get_param_type(param),
                self.create_param_input(param),
                param,
            )
        # Layouts must be defined here
        for index, (name, (param_type, param_input, param)) in enumerate(
            self.input_map.items()
        ):
            param_label = QLabel(name + "<sup><u>?</u></sup>")
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

    def create_param_input(self, param: proc_parsing.inspect.Parameter) -> QWidget:
        __create_map__ = {
            int: self.create_int_param_input,
            float: self.create_float_param_input,
            str: self.create_str_param_input,
        }
        return __create_map__[proc_parsing.get_param_type(param)](param)

    def create_int_param_input(self, param: inspect.Parameter) -> QWidget:
        parser = proc_parsing.get_parser(param)
        # Getting the boundary values
        if parser is None:
            spin_min, spin_max = -999999, 999999
        elif not isinstance(parser, arg_validation.Range):
            spin_min, spin_max = -999999, 999999
        else:
            spin_min, spin_max = parser.min_val, parser.max_val

        # Getting the default values
        if not proc_parsing.has_default(param):
            def_val = int((spin_min + spin_max) / 2)
        else:
            def_val = param.default

        # Returning the created object
        return _QSpinBoxDefault(def_val, min_value=spin_min, max_value=spin_max)

    def create_float_param_input(self, param: inspect.Parameter) -> QWidget:
        # TODO: better way for ensuring the input is a float??
        parser = proc_parsing.get_parser(param)

        # Getting boundary values
        if parser is None:
            spin_min, spin_max = -999999, 9999999
        elif not isinstance(parser, arg_validation.Range):
            spin_min, spin_max = -999999, 9999999
        else:
            spin_min, spin_max = parser.min_val, parser.max_val

        # Getting the default value
        if not proc_parsing.has_default(param):
            def_val = (spin_min + spin_max) / 2
        else:
            def_val = param.default

        # Returning the created object
        return _QDoubleSpinBoxDefault(
            default=def_val, min_value=spin_min, max_value=spin_max
        )

    def create_str_param_input(self, param: inspect.Parameter) -> QWidget:
        parser = proc_parsing.get_parser(param)
        has_def = proc_parsing.has_default(param)
        if parser is None and not has_def:
            return QLineEdit()  # Arbitrary string
        if parser is None and has_def:
            return _QLineEditDefault(param.default)  # String with fall back default
        if isinstance(parser, arg_validation.StringListChecker):
            widget = _QComboPlaceholder("--choose valid string--")
            parser.session = self.session

            for item in parser._full_list:
                widget.addItem(item)
            return widget

    def cast_widget_input(self, arg_type, arg_widget, arg_param) -> Any:
        input_val = None
        if isinstance(arg_widget, QLineEdit):
            input_val = arg_widget.text()
        elif isinstance(arg_widget, _QSpinBoxDefault):
            input_val = arg_widget.value()
        elif isinstance(arg_widget, _QDoubleSpinBoxDefault):
            input_val = arg_widget.value()
        elif isinstance(arg_widget, _QComboPlaceholder):
            input_val = arg_widget.currentText()

        return arg_type(input_val)


class SessionRunSingleProcedure(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self.interupt_button = _QInteruptButton(session, "INTERUPT")
        self.tabs = QTabWidget()
        self.__init_layout__()
        self.interupt_button.clicked.connect(self.send_interupt)

    def __init_layout__(self):
        self._outer = QVBoxLayout()
        self._box = QGroupBox("Run single procedure")
        self._inner = QVBoxLayout()
        self._box.setLayout(self._inner)
        self._outer.addWidget(self._box)
        self.setLayout(self._outer)

        for method_class in procedures.__all_procedures__:
            self.tabs.addTab(
                SingleProcedureTab(self.session, method_class), method_class.__name__
            )
        self._inner.addWidget(self.tabs)
        self._inner.addWidget(self.interupt_button)

    def send_interupt(self):
        """Interupt the current running process"""
        self.session.interupt_flag = True
