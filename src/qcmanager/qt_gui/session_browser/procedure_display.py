import importlib
from typing import Any, Callable, List, Optional, Tuple

import matplotlib
import matplotlib.backends.backend_qt5agg as mplbackend
from PyQt5.QtCore import QAbstractTableModel, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...utils import _str_, timestampg
from ...yaml_format import ProcedureResult, SingularResult, StatusCode
from ..gui_session import GUISession
from ..qt_helper import _QContainer, clear_layout


class _QWrapLabel(QLabel):
    """Helper label to ensure that word wrapping is enabled by default"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWordWrap(True)


class SessionProcedureDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self.list_display = ProcudureSummaryList(self.session)
        self.detail_display = ProcedureTextDisplay(self.session)
        self.__init_layout__()

        # Connecting signals
        self.list_display.display_detailed_signal.connect(
            self.detail_display.display_result
        )

    def __init_layout__(self):
        self._outer = QVBoxLayout()
        self._box = QGroupBox("QA/QC Procedure results")
        self._inner = QHBoxLayout()
        self.setLayout(self._outer)
        self._outer.addWidget(self._box)
        self._box.setLayout(self._inner)

        self._inner.addWidget(self.list_display, stretch=1)
        self._inner.addWidget(self.detail_display, stretch=2)


class ProcedureTextDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)
        self.result = None  # Reference to object to be displayed

        # For overall results
        self.name_label = _QWrapLabel("")
        self.start_label = _QWrapLabel("")
        self.end_label = _QWrapLabel("")
        self.logical_label = _QWrapLabel("")
        self.procedure_args_layout = QFormLayout()
        self.board_summary_layout = QFormLayout()

        # For channel overview and details
        self.channel_overview = QGridLayout()
        self.channel_detail_container = QVBoxLayout()
        self.channel_mapping = {}

        # For buttons for showing the plots
        self.plot_buttons_layout = QHBoxLayout()
        self.plot_widget: Optional[ProcedurePlotDisplay] = None

        self.display_container = QWidget()
        self.message_container = _QWrapLabel("")

        self.__init_layout__()

    def __init_layout__(self):

        self._display_layout = QVBoxLayout()

        self._summary_layout = QHBoxLayout()
        # Adding the various items
        self._board_column = QFormLayout()
        self._board_column.addRow("Procedure name", self.name_label)
        self._board_column.addRow("Start time", self.start_label)
        self._board_column.addRow("End time", self.end_label)
        self._board_column.addRow("Logical status", self.logical_label)
        self._board_column.addRow("Procedure arguments", self.procedure_args_layout)
        self._board_column.addRow("Board summary", self.board_summary_layout)

        self._channel_column = QVBoxLayout()
        self._channel_column.addWidget(QLabel("<b>Channel overview</b>"))
        self._channel_column.addLayout(self.channel_overview)
        self._channel_column.addWidget(QLabel("<b>Per-channel details</b>"))
        self._channel_column.addLayout(self.channel_detail_container)
        self._channel_column.addStretch()

        self._summary_layout.addLayout(self._board_column, stretch=10)
        self._summary_layout.addStretch()
        self._summary_layout.addLayout(self._channel_column, stretch=10)
        self._display_layout.addLayout(self._summary_layout)

        self._plot_layout_wrapper = QFormLayout()
        self._plot_layout_wrapper.addRow("Show Plots", self.plot_buttons_layout)
        self._display_layout.addLayout(self._plot_layout_wrapper)
        self.display_container.setLayout(self._display_layout)

        self._layout = QVBoxLayout()
        self._layout.addWidget(self.display_container)
        self._layout.addWidget(self.message_container)

        self.setLayout(self._layout)

    def display_result(self, result_index: Optional[int] = None):
        if result_index is None:
            self.result = None
        else:
            self.result = self.session.results[result_index]
        self._display_update()
        if self.plot_widget is not None:
            self.plot_widget.display_result(self.result, 0)

    def _display_update(self):
        # Updating the various items
        if self.session.board_id == "" or self.session.board_type == "":
            self.message_container.setText(
                "No session is loaded. Load from the section above"
            )
            self.message_container.show()
            self.display_container.hide()
            return

        if self.result is None:
            self.message_container.setText(
                "No result selection. Please select from left"
            )
            self.message_container.show()
            self.display_container.hide()
            return

        self.message_container.hide()
        self.display_container.show()
        self._display_update_board()
        self._display_update_channel()
        self._display_update_plotbutton()

    def _display_update_board(self):
        self.name_label.setText(self.result.name)
        self.start_label.setText(timestampg(self.result.start_time))
        self.end_label.setText(timestampg(self.result.end_time))
        self.logical_label.setText(self.make_logical_label(self.result.status_code))
        clear_layout(self.procedure_args_layout)
        for k, v in self.result.input.items():
            self.procedure_args_layout.addRow(k, self.make_argument_label(v))
        # Board level summary
        clear_layout(self.board_summary_layout)
        self.board_summary_layout.addRow(
            "Status",
            self.status_summary_label(self.result.board_summary),
        )
        if self.result.board_summary is not None:
            self.add_singleresult_items(
                self.board_summary_layout, self.result.board_summary
            )

    def _display_update_channel(self):
        clear_layout(self.channel_overview)
        clear_layout(self.channel_detail_container.layout())
        self.channel_mapping = {}

        def channel_detail_widget(r: SingularResult):
            container = QWidget()
            layout = QFormLayout()
            layout.addRow("Channel", QLabel(str(res.channel)))
            layout.addRow("Status", self.status_summary_label(res))
            self.add_singleresult_items(layout, r)
            container.setLayout(layout)
            container.hide()
            return container

        def show_index(channel: int):
            def _wrap(event=False):
                for container in self.channel_mapping.values():
                    container.hide()
                self.channel_mapping[channel].show()

            return _wrap

        for idx, res in enumerate(self.result.channel_summary):
            summary = QLabel(str(res.channel))
            summary.setStyleSheet(self.error_styling(res))
            summary.setAlignment(Qt.AlignHCenter)
            self.channel_overview.addWidget(summary, idx // 8, idx % 8)

            detail = channel_detail_widget(res)
            self.channel_detail_container.addWidget(detail)
            self.channel_mapping[res.channel] = detail
            summary.mousePressEvent = show_index(res.channel)

    def _display_update_plotbutton(self):
        clear_layout(self.plot_buttons_layout)
        if self.result is None:
            return
        try:
            plotlib = importlib.import_module(f"qcmanager.plotting.{self.result.name}")
        except Exception:
            return

        plotter = getattr(plotlib, self.result.name)(self.session.save_base)

        for idx, p_name in enumerate(plotter.figure_methods.keys()):
            button = QPushButton(p_name.replace("_", ""))
            self.plot_buttons_layout.addWidget(button)
            button.clicked.connect(self._display_plot_widget(idx))

    def _display_plot_widget(self, plot_index):
        def _call(evt):
            if self.plot_widget is None:
                self.plot_widget = ProcedurePlotDisplay(self.session)

            self.plot_widget.display_result(self.result, plot_index)
            self.plot_widget.show()

        return _call

    @classmethod
    def make_logical_label(cls, status: Tuple[int, str]) -> str:
        if status[0] == StatusCode.SUCCESS:
            return "Complete"
        if status[0] == StatusCode.SIG_INTERUPT:
            return "User Interupted"
        return f"[{status[0]}] {status[1]}"

    @classmethod
    def make_argument_label(cls, argument_value: Any) -> QLabel:
        label_str = str(argument_value)
        if len(label_str) > 30:
            label = QLabel("<u>..." + label_str[-30:] + "</u>")
            label.setToolTip(label_str)
            return label
        else:
            return QLabel(label_str)

    @classmethod
    def add_singleresult_items(cls, layout: QFormLayout, r: SingularResult):
        for k, v in r.__dict__.items():
            if k == "status" or k == "desc" or k == "channel":
                continue
            label = QLabel(str(v))
            label.setWordWrap(True)
            layout.addRow(k, label)

    @classmethod
    def error_styling(self, r: Optional[SingularResult] = None):
        if r is None:
            return "background-color: orange"
        else:
            return (
                "background-color: green" if r.status == 0 else "background-color: red"
            )

    @classmethod
    def status_summary_label(cls, r: Optional[SingularResult] = None):
        if r is None:
            label = QLabel("Not reached!")
        else:
            label = QLabel("Good" if r.status == 0 else f"[{r.status}] {r.desc}")
        label.setStyleSheet(cls.error_styling(r))
        return label


class MplCanvasWidget(QWidget):
    """
    Wrapper for the default matplotlib FigureCanvas and the accompanying
    Navigation tool bar, set in a fixed orientation.
    """

    def __init__(self, figure: matplotlib.figure.Figure):
        super().__init__()
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._figure = figure
        self._canvas = mplbackend.FigureCanvas(self._figure)
        self._toolbar = mplbackend.NavigationToolbar2QT(self._canvas)
        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._canvas)
        self._layout.addStretch()

    def deleteLater(self):
        # Closing figure though matplotlib to ensure memory resources is
        # released.
        matplotlib.pyplot.close(self._figure)
        super().deleteLater()


class ProcedurePlotDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)
        self.result: Optional[ProcedureResult] = None

        # Tab container for the various items
        self.message = QLabel()
        self.plot_view = QTabWidget()
        self.__init_layout__()

    def __init_layout__(self):
        # Additional styling
        self.plot_view.setMinimumWidth(800)
        self.plot_view.setMinimumHeight(600)
        self._layout = QVBoxLayout()
        self._layout.addWidget(self.message)
        self._layout.addWidget(self.plot_view)
        self.setLayout(self._layout)

    def display_result(
        self, result: Optional[ProcedureResult] = None, plot_idx: Optional[int] = None
    ):
        if self.result is not result:
            # Only update if the result request is different
            self.result = result
            self._display_update()

        self.plot_view.setCurrentIndex(plot_idx)

    def _display_update(self):
        # QTabWidget does *not* delete objects when calling the clear object.
        # Explicitly calling deleteLater to force matplotlib figures to be
        # properly released.
        for idx in range(self.plot_view.count()):
            self.plot_view.widget(idx).deleteLater()
        if self.result is None:
            self.message.setText("")
            return  # Early exit

        self.message.setText(
            _str_(
                f"""
                Plots for procedure [{self.result.name}] completed at [{timestampg(self.result.end_time)}]
                """
            )
        )
        try:
            plotlib = importlib.import_module(f"qcmanager.plotting.{self.result.name}")
        except Exception:
            self._layout.addWidget(
                QLabel(f"No plotting methods for procedure [{self.result.name}] found")
            )
            return
        self.setWindowTitle("Procedure results plots")
        plotter = getattr(plotlib, self.result.name)(self.session.save_base)

        for p_name, p_func in plotter.figure_methods.items():
            figure_widget = self._make_single_figure(p_name, p_func)
            self.plot_view.addTab(figure_widget, p_name.replace("_", " "))

    def _make_single_figure(self, plot_name: str, plot_function: Callable):
        try:
            return MplCanvasWidget(plot_function(self.result))
        except Exception as err:
            msg = [
                "Failed to generate plot",
                f"Check function from plotting.{self.result.name}.fig_{plot_name}",
                f"Message: {str(err)}",
            ]
            return QLabel("\n".join(msg))


class ProcedureTableModel(QAbstractTableModel):
    def __init__(self, results_list: List[ProcedureResult]):
        super().__init__()
        self.results_list = results_list  # Setting reference to main results list

    def data(self, index, role):
        if role == Qt.DisplayRole:
            result = self.results_list[index.row()]
            if index.column() == 0:
                return result.name
            if index.column() == 1:
                valid = result.is_valid
                return "Good" if valid else "Failed"
            if index.column() == 2:
                return timestampg(result.end_time)
            else:
                return ""
        if role == Qt.TextAlignmentRole:
            if index.column() != 2:
                return Qt.AlignHCenter | Qt.AlignVCenter
            else:
                return Qt.AlignVCenter

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return "Name"
                if section == 1:
                    return "Result"
                if section == 2:
                    return "End time"
                return ""

            if orientation == Qt.Vertical:
                return section

    def rowCount(self, index):
        return len(self.results_list)

    def columnCount(self, index):
        return 3


class ProcudureSummaryList(_QContainer):
    display_detailed_signal = pyqtSignal(int)

    def __init__(self, session: GUISession):
        super().__init__(session)
        self.table_view = QTableView()
        self.table_model = None  # Updated later
        self.message_label = QLabel("")

        self.__init_layout__()
        self._display_update()
        self.table_view.clicked.connect(self.display_detail)

    def __init_layout__(self):
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.addWidget(self.message_label)
        self._layout.addWidget(self.table_view)
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

    def _display_update(self):
        if self.session.board_id == "":
            self.table_view.hide()
            self.message_label.show()
            self.message_label.setText("No session loaded")
        elif len(self.session.results) == 0:
            self.table_view.hide()
            self.message_label.show()
            self.message_label.setText("No results for session")
        else:
            self.table_view.show()
            self.message_label.hide()
            self.table_model = ProcedureTableModel(self.session.results)
            self.table_view.setModel(self.table_model)

    def display_detail(self, item):
        self.display_detailed_signal.emit(item.row())
